import sys
import os
import pandas as pd
from datetime import datetime
import json
from dotenv import load_dotenv
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QPushButton, QLabel, QFileDialog, QListWidget, QSpinBox, 
    QHBoxLayout, QLineEdit, QMessageBox, QProgressBar, QTextEdit,
    QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO
import zipfile
import re

class LogProcessorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Log Processor")
        self.setMinimumSize(1200, 900)

        # Create a scroll area for the main content
        scroll = QScrollArea()
        self.setCentralWidget(scroll)
        
        # Create main container widget that will be scrollable
        container = QWidget()
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        
        # Main layout with proper spacing
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Log File Processor")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2196F3;
            padding: 10px;
            margin-bottom: 20px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # File Upload Section
        upload_group = QWidget()
        upload_layout = QVBoxLayout(upload_group)
        upload_layout.setSpacing(10)
        upload_layout.setContentsMargins(10, 10, 10, 10)
        
        # List File Section
        list_section = QWidget()
        list_layout = QVBoxLayout(list_section)
        list_layout.setSpacing(5)
        
        list_label = QLabel("List File (CSV):")
        list_label.setStyleSheet("font-weight: bold;")
        list_layout.addWidget(list_label)
        
        list_button = QPushButton("Choose List File")
        list_button.clicked.connect(self.upload_list_file)
        list_layout.addWidget(list_button)
        
        self.list_file_label = QLabel("No file selected")
        list_layout.addWidget(self.list_file_label)
        
        upload_layout.addWidget(list_section)
        
        # Add spacing between sections
        upload_layout.addSpacing(15)
        
        # Log Files Section
        log_section = QWidget()
        log_layout = QVBoxLayout(log_section)
        log_layout.setSpacing(5)
        
        log_label = QLabel("Log Files (CSV):")
        log_label.setStyleSheet("font-weight: bold;")
        log_layout.addWidget(log_label)
        
        log_button = QPushButton("Choose Log Files")
        log_button.clicked.connect(self.upload_log_files)
        log_layout.addWidget(log_button)
        
        self.log_files_list = QListWidget()
        self.log_files_list.setMinimumHeight(100)
        log_layout.addWidget(self.log_files_list)
        
        upload_layout.addWidget(log_section)
        main_layout.addWidget(upload_group)

        # Conditions Section
        conditions_group = QWidget()
        conditions_layout = QVBoxLayout(conditions_group)
        conditions_layout.setSpacing(10)
        conditions_layout.setContentsMargins(10, 10, 10, 10)
        
        conditions_label = QLabel("Add Conditions")
        conditions_label.setStyleSheet("font-weight: bold;")
        conditions_layout.addWidget(conditions_label)
        
        # Condition Input Row
        condition_input = QWidget()
        input_layout = QHBoxLayout(condition_input)
        input_layout.setSpacing(10)
        
        self.condition_type = QLineEdit()
        self.condition_type.setPlaceholderText("Enter Condition Type")
        input_layout.addWidget(self.condition_type)
        
        self.threshold = QSpinBox()
        self.threshold.setMinimum(1)
        self.threshold.setMaximum(9999)
        input_layout.addWidget(self.threshold)
        
        add_button = QPushButton("Add")
        add_button.clicked.connect(self.add_condition)
        input_layout.addWidget(add_button)
        
        conditions_layout.addWidget(condition_input)
        
        # Conditions List
        self.conditions_list = QListWidget()
        self.conditions_list.setMinimumHeight(100)
        conditions_layout.addWidget(self.conditions_list)
        
        main_layout.addWidget(conditions_group)

        # Progress Section
        progress_group = QWidget()
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(10)
        progress_layout.setContentsMargins(10, 10, 10, 10)
        
        progress_label = QLabel("Progress")
        progress_label.setStyleSheet("font-weight: bold;")
        progress_layout.addWidget(progress_label)
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMinimumHeight(100)
        progress_layout.addWidget(self.status_text)
        
        main_layout.addWidget(progress_group)

        # Process Button
        self.process_button = QPushButton("Process Files")
        self.process_button.setEnabled(False)
        self.process_button.setMinimumHeight(40)
        self.process_button.clicked.connect(self.process_files)
        self.process_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                margin-top: 20px;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        main_layout.addWidget(self.process_button)

        # Initialize variables
        self.list_file = None
        self.log_files = []
        self.conditions = []
        
        # Google Drive settings
        self.REMOVED_FOLDER_ID = "18evx04gWua9ls1mDiIr5FvAQhdFbrwfr"
        self.SCRUBBED_FOLDER_ID = "1-jYrCY5ev44Hy5fXVwOZSjw7xPSTy9ML"
        self.service = None
        
        # Initialize Google Drive service
        QTimer.singleShot(0, self.initialize_drive_service)

        # Apply global styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F5F5;
            }
            QLabel {
                font-size: 14px;
            }
            QPushButton {
                padding: 8px;
                font-size: 14px;
            }
            QListWidget {
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                background-color: white;
            }
            QLineEdit, QSpinBox {
                padding: 8px;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
            }
            QWidget {
                background-color: transparent;
            }
        """)

    def upload_list_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select List File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_name:
            self.list_file = file_name
            self.list_file_label.setText(os.path.basename(file_name))
            self.update_process_button()

    def upload_log_files(self):
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Log Files",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_names:
            self.log_files.extend(file_names)
            self.log_files_list.clear()
            for file in self.log_files:
                self.log_files_list.addItem(os.path.basename(file))
            self.update_process_button()

    def add_condition(self):
        condition_type = self.condition_type.text().strip()
        threshold = self.threshold.value()
        
        if condition_type:
            condition_text = f"{condition_type} - min Count: {threshold}"
            self.conditions_list.addItem(condition_text)
            self.conditions.append({"type": condition_type, "threshold": threshold})
            self.condition_type.clear()
            self.threshold.setValue(1)
            self.update_process_button()

    def update_process_button(self):
        self.process_button.setEnabled(
            bool(self.list_file) and 
            bool(self.log_files) and 
            bool(self.conditions)
        )

    def process_files(self):
        """Process the files"""
        try:
            self.process_button.setEnabled(False)
            self.progress_bar.setValue(0)
            self.update_status("Starting file processing...")

            # Process files
            self.update_status("Processing files...", 10)
            updated_list_df, updated_log_dfs, removed_log_records = self.process_data(
                self.log_files, 
                self.list_file,
                self.conditions, 
                [self.log_files_list.item(i).text() for i in range(self.log_files_list.count())]
            )

            # Upload to Google Drive
            current_date = datetime.now().strftime("%Y%m%d")
            
            # Upload updated list file
            self.update_status("Uploading processed files to Google Drive...", 70)
            list_io = BytesIO()
            updated_list_df.to_csv(list_io, index=False)
            list_io.seek(0)
            self.upload_to_drive(
                f"Updated_List_{current_date}.csv",
                list_io,
                self.REMOVED_FOLDER_ID
            )

            # Upload log files and removed records
            for i, (log_df, rem_df) in enumerate(zip(updated_log_dfs, removed_log_records), 1):
                log_name = self.log_files_list.item(i-1).text()
                progress = 70 + (i / len(updated_log_dfs) * 20)
                self.progress_bar.setValue(progress)
                
                # Upload scrubbed log
                log_io = BytesIO()
                log_df.to_csv(log_io, index=False)
                log_io.seek(0)
                self.upload_to_drive(
                    f"Scrubbed_{log_name}_{current_date}.csv",
                    log_io,
                    self.SCRUBBED_FOLDER_ID
                )

                # Upload removed records if they exist
                if not rem_df.empty:
                    rem_io = BytesIO()
                    rem_df.to_csv(rem_io, index=False)
                    rem_io.seek(0)
                    self.upload_to_drive(
                        f"Removed_Records_{log_name}_{current_date}.csv",
                        rem_io,
                        self.REMOVED_FOLDER_ID
                    )

            self.update_status("Creating download package...", 90)
            
            # Create local zip file
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add updated list file
                list_csv = BytesIO()
                updated_list_df.to_csv(list_csv, index=False)
                list_csv.seek(0)
                zip_file.writestr(f"Updated_List_{current_date}.csv", list_csv.getvalue())

                # Add log files and their removed records
                for i, (log_df, rem_df) in enumerate(zip(updated_log_dfs, removed_log_records)):
                    log_name = self.log_files_list.item(i).text()
                    
                    # Add scrubbed log
                    log_csv = BytesIO()
                    log_df.to_csv(log_csv, index=False)
                    log_csv.seek(0)
                    zip_file.writestr(f"Scrubbed_{log_name}_{current_date}.csv", log_csv.getvalue())

                    # Add removed records if they exist
                    if not rem_df.empty:
                        rem_csv = BytesIO()
                        rem_df.to_csv(rem_csv, index=False)
                        rem_csv.seek(0)
                        zip_file.writestr(f"Removed_Records_{log_name}_{current_date}.csv", 
                                        rem_csv.getvalue())

            # Save zip file
            zip_buffer.seek(0)
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Processed Files", f"processed_files_{current_date}.zip", 
                "ZIP Files (*.zip)")
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(zip_buffer.getvalue())
                self.update_status(f"Saved processed files to {save_path}")

            self.progress_bar.setValue(100)
            self.update_status("Processing completed successfully!")
            QMessageBox.information(self, "Success", 
                "Files processed and saved successfully!\nUploaded to Google Drive and saved locally.")

        except Exception as e:
            self.update_status(f"Error during processing: {str(e)}")
            QMessageBox.critical(self, "Error", f"Processing failed: {str(e)}")
        finally:
            self.process_button.setEnabled(True)
    def process_data(self, log_dfs, list_df, conditions, log_filenames):
        """Process the data using conditions"""
        try:
            self.update_status("Starting data processing...")
            self.progress_bar.setValue(10)

            # Define function to clean dataframes
            def clean_df(df):
                """Replace all NaN values with empty strings"""
                return df.fillna('').replace(['nan', 'NaN', 'NaT'], '')

            # Clean input dataframes
            list_df = clean_df(list_df)
            log_dfs = [clean_df(df) for df in log_dfs]

            # Normalize list file phone numbers
            list_df["Phone"] = list_df["Phone"].astype(str).apply(self.clean_number)
            self.update_status("Normalized phone numbers in list file")
            self.progress_bar.setValue(20)

            # Compute occurrences
            list_occurrences = (
                list_df.groupby(["Log Type", "Phone"])
                .size()
                .reset_index(name="occurrence")
            )
            list_df = pd.merge(list_df, list_occurrences, on=["Log Type", "Phone"], how="left")
            self.update_status("Computed phone number occurrences")
            self.progress_bar.setValue(30)

            # Initialize containers
            updated_log_dfs = []
            removed_log_records = []

            # Parse conditions and identify numbers to remove
            self.update_status("Applying conditions...")
            parsed_conditions = {cond["type"].title(): cond["threshold"] for cond in conditions}
            cleaned_phones_to_remove = []

            for cond_type, threshold in parsed_conditions.items():
                matching_numbers = list_df.loc[
                    (list_df["Log Type"].str.title() == cond_type) &
                    (list_df["occurrence"] >= threshold), 
                    "Phone"
                ].unique()

                if len(matching_numbers) > 0:
                    cleaned_phones_to_remove.extend([self.clean_number(phone) for phone in matching_numbers])
                    self.update_status(f"Found {len(matching_numbers)} numbers matching condition: {cond_type}")

            # Remove duplicates from numbers to remove
            cleaned_phones_to_remove = list(set(cleaned_phones_to_remove))
            self.progress_bar.setValue(50)

            # Process each log file
            total_logs = len(log_dfs)
            for i, (log_df, filename) in enumerate(zip(log_dfs, log_filenames), 1):
                self.update_status(f"Processing log file {i}/{total_logs}: {filename}")
                
                processed_log_df = log_df.copy()
                removed_records_df = pd.DataFrame()

                # Normalize column names
                processed_log_df.columns = processed_log_df.columns.str.strip().str.lower()
                processed_log_df = clean_df(processed_log_df)

                # Find phone columns
                phone_columns = [
                    col for col in processed_log_df.columns
                    if any(phrase in col.lower() for phrase in ['mobile', 'phone', 'number', 'tel', 'contact', 'ph'])
                ]

                if not phone_columns:
                    self.update_status(f"No phone columns found in {filename}")
                    updated_log_dfs.append(processed_log_df)
                    removed_log_records.append(pd.DataFrame())
                    continue

                # Process phone columns
                rows_with_removed_numbers = set()
                for col in phone_columns:
                    self.update_status(f"Processing column: {col}")
                    processed_log_df[col] = processed_log_df[col].astype(str).apply(
                        lambda x: f"{int(float(x))}" if x.replace(".", "").isdigit() else x
                    )
                    original_values = processed_log_df[col].copy()
                    cleaned_column = processed_log_df[col].apply(self.clean_number)

                    # Remove matching numbers
                    remove_mask = cleaned_column.isin(cleaned_phones_to_remove)
                    if remove_mask.any():
                        # Store rows that had numbers removed
                        for idx in processed_log_df[remove_mask].index:
                            if idx not in rows_with_removed_numbers:
                                removed_row = processed_log_df.loc[idx].copy()
                                # Only keep the removed number in the current column
                                for phone_col in phone_columns:
                                    removed_row[phone_col] = original_values[idx] if phone_col == col else ''
                                rows_with_removed_numbers.add(idx)
                                removed_records_df = pd.concat([removed_records_df, 
                                                          pd.DataFrame([removed_row])], 
                                                          ignore_index=True)
                        
                        processed_log_df.loc[remove_mask, col] = ''
                        self.update_status(f"Removed {remove_mask.sum()} numbers from {col}")

                # Clean final dataframes
                processed_log_df = clean_df(processed_log_df)
                removed_records_df = clean_df(removed_records_df)

                # Add processed dataframes to lists
                updated_log_dfs.append(processed_log_df)
                removed_log_records.append(removed_records_df)

                progress = 50 + (i / total_logs * 40)
                self.progress_bar.setValue(progress)

            self.update_status("Data processing completed!")
            return clean_df(list_df), updated_log_dfs, removed_log_records

        except Exception as e:
            self.update_status(f"Error processing data: {str(e)}")
            raise e

    def clean_df(self, df):
        """Replace all NaN values with empty strings"""
        return df.fillna('').replace(['nan', 'NaN', 'NaT'], '')

    def clean_number(self, phone):
        """Clean and standardize phone numbers"""
        phone = str(phone)
        phone = re.sub(r'\D', '', phone)
        if phone.startswith('1') and len(phone) > 10:
            phone = phone[1:]
        return phone

    def initialize_drive_service(self):
        """Initialize Google Drive service"""
        try:
            credentials = Credentials.from_service_account_file(
                'credentials.json',
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            self.service = build('drive', 'v3', credentials=credentials)
        except Exception as e:
            self.status_text.append(f"Failed to initialize Drive service: {str(e)}")

def main():
    app = QApplication(sys.argv)
    window = LogProcessorApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
