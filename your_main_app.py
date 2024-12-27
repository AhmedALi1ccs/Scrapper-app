import streamlit as st
import pandas as pd
from io import BytesIO, StringIO
import re
import numpy as np
from google.oauth2.service_account import Credentials
import os
import json
import io
from dotenv import load_dotenv
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build
from google.oauth2 import service_account
import zipfile
from datetime import datetime
load_dotenv()

# Constants
SCOPES = ['https://www.googleapis.com/auth/drive']
REMOVED_FOLDER_ID = "1NWv0AjsOF-_5lmsEyL1q20liFWn1CtUk"  # Folder for "removed" files
SCRUBBED_FOLDER_ID = "1Ink3w5hpU5sAx9EvFmPu33W7HIbE1BIz"  # Fixed folder ID

def clean_nan_values(df):
    """
    Replace NaN values with empty strings in the DataFrame
    """
    return df.replace({np.nan: '', 'nan': '', 'NaN': ''})
def clean_number_to_text(df):
    """
    Converts all numeric columns to string with integer formatting (no decimals).
    Simulates Excel's =TEXT(A1, "0") functionality.
    
    Args:
        df (pd.DataFrame): DataFrame to process.

    Returns:
        pd.DataFrame: Processed DataFrame with numeric columns converted to strings.
    """
    for col in df.columns:
        # Check if the column is numeric
        if pd.api.types.is_numeric_dtype(df[col]):
            # Convert numeric column to formatted strings without decimals
            df[col] = df[col].apply(lambda x: f"{int(x)}" if pd.notnull(x) else "")
    return df
def create_zip_file(dfs_dict):
    """
    Create a zip file containing all CSV files
    """
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, df in dfs_dict.items():
            # Convert dataframe to CSV
            csv_buffer = BytesIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            
            # Add CSV to zip file - ensure only one .csv extension
            if filename.endswith('.csv'):
                zip_file.writestr(filename, csv_buffer.getvalue())
            else:
                zip_file.writestr(f"{filename}.csv", csv_buffer.getvalue())
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def authenticate():
    """
    Authenticate Google Drive API
    """
    try:
        credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if not credentials_json:
            raise ValueError("GOOGLE_CREDENTIALS_JSON not found in environment variables.")
        
        credentials_dict = json.loads(credentials_json)
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        st.info("Google Drive authenticated successfully.")
        return service
    except Exception as e:
        st.error(f"Google Drive authentication failed: {e}")
        raise e

def upload_to_drive_from_memory(file_name, file_data, folder_id):
    """
    Upload a file directly from memory to Google Drive
    """
    try:
        file_metadata = {
            'name': file_name,
            'parents': [folder_id],
        }
        media = MediaIoBaseUpload(file_data, mimetype='text/csv', resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        st.success(f"Uploaded {file_name} to Google Drive successfully! File ID: {file.get('id')}")
        return file.get('id')
    except Exception as e:
        st.error(f"Failed to upload {file_name}: {e}")
        raise e

def clean_number(phone):
    """
    Clean and standardize phone numbers consistently
    """
    phone = str(phone)
    phone = re.sub(r'\D', '', phone)
    if phone.startswith('1') and len(phone) > 10:
        phone = phone[1:]
    return phone

def process_files(log_dfs, list_df, conditions, log_filenames):
    """
    Process log files by removing specific phone numbers based on conditions.
    Returns separate removed records for each log file with only the removed numbers.
    """
    # Normalize list file phone numbers
    list_df["Phone"] = list_df["Phone"].astype(str).apply(clean_number)

    # Compute occurrences in the list file
    list_occurrences = (
        list_df.groupby(["Log Type", "Phone"])
        .size()
        .reset_index(name="occurrence")
    )
    list_df = pd.merge(list_df, list_occurrences, on=["Log Type", "Phone"], how="left")

    # Initialize containers
    removed_from_list = pd.DataFrame()
    updated_log_dfs = []
    removed_log_records = []

    # Parse conditions into a dictionary
    parsed_conditions = {cond["type"].title(): cond["threshold"] for cond in conditions}

    # Identify numbers to remove based on conditions
    cleaned_phones_to_remove = []
    for cond_type, threshold in parsed_conditions.items():
        matching_numbers = list_df.loc[
            (list_df["Log Type"].str.title() == cond_type) &
            (list_df["occurrence"] >= threshold), 
            "Phone"
        ].unique()

        if len(matching_numbers) > 0:
            current_removed = list_df[list_df["Phone"].isin(matching_numbers)]
            removed_from_list = pd.concat([removed_from_list, current_removed])
            list_df = list_df[~list_df["Phone"].isin(matching_numbers)]
            cleaned_phones_to_remove.extend([clean_number(phone) for phone in matching_numbers])

    # Remove duplicates from cleaned_phones_to_remove
    cleaned_phones_to_remove = list(set(cleaned_phones_to_remove))
    print("Numbers to remove (cleaned):", cleaned_phones_to_remove)
    
    # Process each log file
    for log_df, filename in zip(log_dfs, log_filenames):
        processed_log_df = log_df.copy()
        removed_records = []  # Will store rows with their removed numbers

        # Normalize column names
        processed_log_df.columns = processed_log_df.columns.str.strip().str.lower()
        processed_log_df = processed_log_df.astype(str)
        processed_log_df = clean_number_to_text(processed_log_df)

        # Identify potential phone number columns
        phone_columns = [
            col for col in processed_log_df.columns
            if any(phrase in col.lower() for phrase in ['mobile', 'phone', 'number', 'tel', 'contact', 'ph'])
        ]
        print(f"\nProcessing file: {filename}")
        print("Phone columns detected:", phone_columns)

        if not phone_columns:
            print(f"No phone columns found in {filename}")
            updated_log_dfs.append(processed_log_df)
            removed_log_records.append(pd.DataFrame())
            continue

        # Track rows that had numbers removed along with the removed numbers
        for col in phone_columns:
            # Clean the column's phone numbers
            processed_log_df[col] = processed_log_df[col].astype(str).apply(
                lambda x: f"{int(float(x))}" if x.replace(".", "").isdigit() else x
            )
            processed_log_df = clean_number_to_text(processed_log_df)
            original_values = processed_log_df[col].copy()  # Store original values
            cleaned_column = processed_log_df[col].apply(clean_number)
            
            # Identify rows to remove
            remove_mask = cleaned_column.isin(cleaned_phones_to_remove)
            
            if remove_mask.any():
                # For each row where a number was removed, store the row with only the removed number
                for idx in processed_log_df[remove_mask].index:
                    removed_row = processed_log_df.loc[idx].copy()
                    original_number = original_values[idx]  # Get the original number that was removed
                    
                    # Clear all phone columns in the removed row
                    for phone_col in phone_columns:
                        removed_row[phone_col] = ''
                    
                    # Put back only the removed number in the current column
                    removed_row[col] = original_number
                    removed_records.append(removed_row)
                
                # Replace matching numbers with empty string in processed DataFrame
                processed_log_df.loc[remove_mask, col] = ''

        # Create removed records DataFrame for this log file
        if removed_records:
            removed_records_df = pd.DataFrame(removed_records)
            removed_records_df = clean_nan_values(removed_records_df)
        else:
            removed_records_df = pd.DataFrame()

        # Clean NaN values from processed log DataFrame
        processed_log_df = clean_nan_values(processed_log_df)

        # Add the processed DataFrames to their respective lists
        updated_log_dfs.append(processed_log_df)
        removed_log_records.append(removed_records_df)

    # Clean NaN values from list DataFrames
    list_df = clean_nan_values(list_df)
    removed_from_list = clean_nan_values(removed_from_list)

    return list_df, updated_log_dfs, removed_log_records
# Initialize Streamlit app
st.title("Log and List File Processor")

# Initialize Google Drive service
service = authenticate()

# Initialize session state
if "list_file" not in st.session_state:
    st.session_state.list_file = None
if "log_files" not in st.session_state:
    st.session_state.log_files = []
if "log_filenames" not in st.session_state:
    st.session_state.log_filenames = []
if "conditions" not in st.session_state:
    st.session_state.conditions = []

# File upload section
st.header("Upload Files")

# List file uploader
uploaded_list_file = st.file_uploader("Upload List File (CSV)", type="csv")
if uploaded_list_file:
    st.session_state.list_file = pd.read_csv(uploaded_list_file)
    st.session_state.list_file_name = os.path.splitext(uploaded_list_file.name)[0]

# Log files uploader
uploaded_log_files = st.file_uploader("Upload Log Files (CSV)", type="csv", accept_multiple_files=True)
if uploaded_log_files:
    st.session_state.log_files = [pd.read_csv(file) for file in uploaded_log_files]
    st.session_state.log_filenames = [file.name for file in uploaded_log_files]

# Display uploaded files and set conditions
if st.session_state.list_file is not None and st.session_state.log_files:
    list_file = st.session_state.list_file
    log_files = st.session_state.log_files
    log_filenames = st.session_state.log_filenames

    st.write("List File Preview:")
    st.dataframe(list_file)
    st.write(f"{len(log_files)} Log Files Uploaded")

    # Conditions section
    st.header("Set Conditions")
    condition_type = st.text_input("Enter Condition Type (e.g., voicemail, call):").capitalize()
    condition_threshold = st.number_input("Enter Threshold (Occurrence Count):", min_value=1, step=1)

    if st.button("Add Condition"):
        st.session_state.conditions.append({
            "type": condition_type,
            "threshold": condition_threshold
        })
        st.success(f"Condition added: {condition_type} with threshold {condition_threshold}")

    st.write("Current Conditions:")
    if st.session_state.conditions:
        for idx, cond in enumerate(st.session_state.conditions):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"{cond['type']} - min Count: {cond['threshold']}")
            with col2:
                if st.button("Remove", key=f"remove_{idx}"):
                    st.session_state.conditions.pop(idx)
                    st.success(f"Removed condition: {cond['type']} with threshold {cond['threshold']}")
                    st.experimental_rerun()
    else:
        st.info("No conditions added yet.")

    # Process files button
    if st.button("Process Files"):
        try:
            if not st.session_state.get("conditions"):
                st.error("Please add at least one condition before processing.")
            else:
                # Get current date for filenames
                current_date = datetime.now().strftime("%Y%m%d")
                
                # Process the files
                updated_list_df, updated_log_dfs, removed_log_records = process_files(
                    log_files, list_file, st.session_state.conditions, log_filenames
                )
                updated_list_df = updated_list_df.drop_duplicates()

                # Store results in session state
                st.session_state.updated_list_df = updated_list_df
                st.session_state.updated_log_dfs = updated_log_dfs
                st.session_state.removed_log_records = removed_log_records
                list_file_name = st.session_state.list_file_name

                # Remove .csv extension if present in list filename
                list_file_base = list_file_name.replace('.csv', '')

                # Upload updated list file to Google Drive
                updated_list_io = BytesIO()
                updated_list_df.to_csv(updated_list_io, index=False)
                updated_list_io.seek(0)
                upload_to_drive_from_memory(
                    f"Updated_{list_file_base}_{current_date}.csv",
                    updated_list_io,
                    REMOVED_FOLDER_ID
                )

                # Upload each log file and its corresponding removed records
                for i, log_file_name in enumerate(log_filenames):
                    # Remove .csv extension if present
                    log_base_name = log_file_name.replace('.csv', '')
                    
                    # Upload scrubbed log file
                    scrubbed_log_io = BytesIO()
                    st.session_state.updated_log_dfs[i].to_csv(scrubbed_log_io, index=False)
                    scrubbed_log_io.seek(0)
                    upload_to_drive_from_memory(
                        f"Scrubbed_{log_base_name}_{current_date}.csv",
                        scrubbed_log_io,
                        SCRUBBED_FOLDER_ID
                    )

                    # Upload removed records if they exist
                    if not st.session_state.removed_log_records[i].empty:
                        removed_log_io = BytesIO()
                        st.session_state.removed_log_records[i].to_csv(removed_log_io, index=False)
                        removed_log_io.seek(0)
                        upload_to_drive_from_memory(
                            f"Removed_Records_{log_base_name}_{current_date}.csv",
                            removed_log_io,
                            REMOVED_FOLDER_ID
                        )

                st.success("Files processed and uploaded successfully!")

                # Prepare files for download
                dfs_to_zip = {
                    f'Updated_List_File_{current_date}': st.session_state.updated_list_df
                }
                
                # Add log files and their removed records to the zip dictionary
                for i, log_file_name in enumerate(st.session_state.log_filenames):
                    log_base_name = log_file_name.replace('.csv', '')
                    dfs_to_zip[f'Scrubbed_{log_base_name}_{current_date}'] = st.session_state.updated_log_dfs[i]
                    
                    if not st.session_state.removed_log_records[i].empty:
                        dfs_to_zip[f'Removed_Records_{log_base_name}_{current_date}'] = st.session_state.removed_log_records[i]

                # Create and offer zip download
                zip_content = create_zip_file(dfs_to_zip)

                # Show success message and download button
                st.success("Processing complete! You can now download all files.")
                st.download_button(
                    label="⬇️ Download All Processed Files",
                    data=zip_content,
                    file_name=f"all_processed_files_{current_date}.zip",
                    mime="application/zip",
                )

                # Display previews section
                st.subheader("File Previews")
                st.write("Updated List File:")
                st.dataframe(st.session_state.updated_list_df)

                # Optional detailed previews
                if st.checkbox("Show detailed file previews"):
                    for i, log_file_name in enumerate(st.session_state.log_filenames):
                        st.write(f"\nProcessed Log File: {log_file_name}")
                        st.dataframe(st.session_state.updated_log_dfs[i])
                        
                        if not st.session_state.removed_log_records[i].empty:
                            st.write(f"Removed Records from {log_file_name}")
                            st.dataframe(st.session_state.removed_log_records[i])

        except Exception as e:
            st.error(f"Error processing files: {e}")
            print(f"Detailed error: {str(e)}")  # For debugging
    # Display results and download options
    if "updated_list_df" in st.session_state:
        st.subheader("Updated List File")
        st.dataframe(st.session_state.updated_list_df)

        # Prepare zip file with all processed files
        dfs_to_zip = {
            'Updated_List_File': st.session_state.updated_list_df
        }
        
        for i, log_file_name in enumerate(st.session_state.log_filenames):
            dfs_to_zip[f'Scrubbed_{log_file_name}'] = st.session_state.updated_log_dfs[i]
            
            if not st.session_state.removed_log_records[i].empty:
                dfs_to_zip[f'Removed_Records_{log_file_name}'] = st.session_state.removed_log_records[i]

        # Create and offer zip download
        zip_content = create_zip_file(dfs_to_zip)
        st.download_button(
            label="⬇️ Download All Processed Files",
            data=zip_content,
            file_name="all_processed_files.zip",
            mime="application/zip",
        )

        # Optional file previews
        if st.checkbox("Show Individual File Previews"):
            st.subheader("Log Files")
            for i, log_file_name in enumerate(st.session_state.log_filenames):
                st.write(f"Preview of Scrubbed Log File ({log_file_name})")
                st.dataframe(st.session_state.updated_log_dfs[i])
                
                if not st.session_state.removed_log_records[i].empty:
                    st.write(f"Preview of Removed Records ({log_file_name})")
                    st.dataframe(st.session_state.removed_log_records[i])