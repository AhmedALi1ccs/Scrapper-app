import sys
import os
import pandas as pd
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QPushButton, QLabel, QFileDialog, QListWidget, QSpinBox, QHBoxLayout,
    QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO
import zipfile
from datetime import datetime

class LogProcessorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Log Processor")
        self.setMinimumSize(900, 700)  # Increased window size
        self.setContentsMargins(20, 20, 20, 20)  # Add some padding
    
        # Initialize variables
        self.list_file = None
        self.log_files = []
        self.conditions = []
        
        # Create main widget with padding
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)  # Add space between elements
    
        # Create UI elements with headers
        title_label = QLabel("Log File Processor")
        title_label.setStyleSheet("""
            font-size: 24px;
            color: #1976D2;
            font-weight: bold;
            margin-bottom: 20px;
        """)
        layout.addWidget(title_label)
    
        # Create sections
        self.create_upload_section(layout)
        layout.addSpacing(20)  # Add space between sections
        self.create_conditions_section(layout)
        layout.addSpacing(20)
        self.create_process_button(layout)
    
        # Style the UI
        self.style_ui()

    def style_ui(self):
        """Apply modern styling to the UI elements"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
            
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                min-width: 120px;
                font-size: 14px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #1976D2;
                transform: translateY(-1px);
            }
            
            QPushButton:pressed {
                background-color: #1565C0;
            }
            
            QPushButton:disabled {
                background-color: #BBDEFB;
                color: #90CAF9;
            }
            
            QLabel {
                font-size: 14px;
                color: #2c3e50;
                font-weight: bold;
                margin: 8px 0;
            }
            
            QListWidget {
                border: 2px solid #e8e8e8;
                border-radius: 8px;
                padding: 5px;
                background-color: white;
            }
            
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }
            
            QListWidget::item:hover {
                background-color: #f0f0f0;
            }
            
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976D2;
            }
            
            QLineEdit {
                padding: 10px;
                border: 2px solid #e8e8e8;
                border-radius: 6px;
                background-color: white;
            }
            
            QLineEdit:focus {
                border-color: #2196F3;
            }
            
            QSpinBox {
                padding: 10px;
                border: 2px solid #e8e8e8;
                border-radius: 6px;
                background-color: white;
            }
            
            QSpinBox:focus {
                border-color: #2196F3;
            }
            
            QMessageBox {
                background-color: white;
            }
            
            QMessageBox QPushButton {
                min-width: 100px;
                padding: 8px 16px;
            }
        """)

    def create_upload_section(self, layout):
        """Create the file upload section"""
        # List file upload
        list_label = QLabel("Upload List File (CSV):")
        layout.addWidget(list_label)
        
        list_button = QPushButton("Choose List File")
        list_button.clicked.connect(self.upload_list_file)
        layout.addWidget(list_button)

        self.list_file_label = QLabel("No file selected")
        layout.addWidget(self.list_file_label)

        # Log files upload
        log_label = QLabel("Upload Log Files (CSV):")
        layout.addWidget(log_label)
        
        log_button = QPushButton("Choose Log Files")
        log_button.clicked.connect(self.upload_log_files)
        layout.addWidget(log_button)

        self.log_files_list = QListWidget()
        layout.addWidget(self.log_files_list)

    def create_conditions_section(self, layout):
        """Create the conditions section"""
        conditions_label = QLabel("Set Conditions:")
        layout.addWidget(conditions_label)

        # Condition input layout
        condition_layout = QHBoxLayout()
        
        self.condition_type = QLineEdit()
        self.condition_type.setPlaceholderText("Enter Condition Type")
        condition_layout.addWidget(self.condition_type)

        self.threshold = QSpinBox()
        self.threshold.setMinimum(1)
        condition_layout.addWidget(self.threshold)

        add_condition_button = QPushButton("Add Condition")
        add_condition_button.clicked.connect(self.add_condition)
        condition_layout.addWidget(add_condition_button)

        layout.addLayout(condition_layout)

        # Conditions list
        self.conditions_list = QListWidget()
        layout.addWidget(self.conditions_list)

    def create_process_button(self, layout):
        """Create the process button"""
        self.process_button = QPushButton("Process Files")
        self.process_button.clicked.connect(self.process_files)
        self.process_button.setEnabled(False)
        layout.addWidget(self.process_button)

    def authenticate(self):
        """Authenticate Google Drive API"""
        try:
            credentials_json = {
                "type": "service_account",
                "project_id": "fluent-vortex-441616-c0",
                "private_key_id": "95db41d1457c184fb5162f337e135257e9f24312",
                "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDQ9tdSKlYXp4gz\nFpFf3kYZ7f7Ry3ZWqPpp7FPL/WME9UhVEOC+Hs++zltMGw2uBtVvG5P++CCL7bdq\nRp7cFxUKh0vIiIZMZJIyBpuJucaqnOl+OAp/zr9Wt21KGnxuYd/ruT4M430ro3sx\nZC6llQm9vv1C5WrFNV3Cng05+lsawOORZHAWbssOWmwNhYjWnMGSYwkEios76E4A\n7tw7gZMwZ3qv5j7QSI9No7/igNBKRqEQ6fG/3H+LzAe30qBFMRDzjL9C/a4H2m5q\nz0JNSO03EqcqeT9ymxQBUZ65gej7aHH05o5KBvlBLlBtDmRLVgc4LyBCkzH9l5Hn\nTh/3CpaRAgMBAAECggEAC9KNqh2wgPisiCiP/wPT7hPqk0V7fvCHpv0XOAkwZo+O\nERe6E/ngSsiYDE+Jz+ILYZSY2xekvFOttwP+aS/n/P4Td7LgjkbC8rTCbOGnb6bV\nUeT0XWZ9zkCb5eQeA4y+VcUg0XRuBl+Zmf1YUSLNXG4r93KEPqPNBX2jajec5Dak\nNmVKts4lBtdI264F2mkXdMXlzXZl/XQfBWx1H2mIXHdFSpeiRW1b/rQnRDW+CEDT\nYYZKUVyRG/ElMDXKlz9usbZT3l4eKwVXSC8BKIQwjjmZCO5ScgyGkWVAPpZEECJG\nCADRIpVzAaOLGuRYZZP5RlFg/e1/NDIO1owhy+tUhQKBgQDyMH6AkeTE2MqW+YWi\nL1gBOs+5QTsLJPjwVrI9WaPAEpJdSm00eeH52p9hvR0YoyEdZVLXjIn26V4wmIlM\nijzuNaZh7YLF1LNMYDcoZjD7DnkKcg615p9flztD57BzZPYw00QJ1VjW5kbUicsN\nS/O8g1Au5aKAKLT8JYkpYFGRowKBgQDc4VJu8aLckVPYYn/W69Tm1nYMDn5wEnMO\ndIw9AjZLMQgxiWPVgX+5wF+7nU5WQP45iy7Co5p7qKeozz9to2YPWb9GplmAtI2F\nnSbZBqG//D6RCRAV01h8JnAnmehlULrB6AEvWRJ4s5iJYVLLmJfrIagU98TaeDY+\nFxkkT6ZCOwKBgD8D1yZkz31YWv4FVnvojaFkSAAPtOklaZA/Pokv9adYLbUQVHG+\n9Mkp1SZ9KkDq0QbxAikLbCpOdi92wOKlZU0lsHDyd4A5450Pu8pLLJtmHKBXJPS3\nWOhqVQVKF2Mu9c+maKGWXVMs/2j1oVuIU5bNI+PP5AQsk0q4CYQ2h4K5AoGAATvI\n6BG1ZSHyo+y45gxfHgLomdyi3CFePyBrgBO5FeZqM0yfIBwfCHyIjFWukFDAmrWq\nRy/+tt4UQZ8WrZgSA9fud4iKS2u2tp5QDzo4QQg5mTnBuz146wiT68SyRY6T3G1d\nRFRtA/uMyIegnL53arq/Y46WrNmrA+HBJDDFru0CgYAwi7AaYZ5qsh/t0PeYiBrT\n5+O4U7bZHaw33lIkpPVqsI6fHEY5kIjwBiXlcr3QX3G3OWzIvVC4KTe9PIbLFZ1h\nWiYcur8mYdLT6gA2wXklLPadhnpFiupVw1A795UUAvcTZ6dcnseWjcB9dfnvZO4m\nuJivtfQgWIer3wP4Rb6tvQ==\n-----END PRIVATE KEY-----\n",
                "client_email": "python-api@fluent-vortex-441616-c0.iam.gserviceaccount.com",
                "client_id": "114288392628833734729",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/python-api%40fluent-vortex-441616-c0.iam.gserviceaccount.com"
            }
            
            creds = Credentials.from_service_account_info(credentials_json, 
                scopes=['https://www.googleapis.com/auth/drive'])
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to authenticate: {str(e)}")
            return None

    def upload_to_drive(self, file_name, file_data, folder_id):
        """Upload a file to Google Drive"""
        try:
            file_metadata = {
                'name': file_name,
                'parents': [folder_id],
            }
            media = MediaIoBaseUpload(file_data, mimetype='text/csv', resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            return file.get('id')
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to upload {file_name}: {str(e)}")
            return None

    def upload_list_file(self):
        """Handle list file upload"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select List File", "", "CSV Files (*.csv)")
        if file_name:
            try:
                self.list_file = pd.read_csv(file_name)
                self.list_file_label.setText(os.path.basename(file_name))
                self.update_process_button()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read file: {str(e)}")

    def upload_log_files(self):
        """Handle log files upload"""
        file_names, _ = QFileDialog.getOpenFileNames(
            self, "Select Log Files", "", "CSV Files (*.csv)")
        if file_names:
            self.log_files = []
            self.log_files_list.clear()
            for file_name in file_names:
                try:
                    df = pd.read_csv(file_name)
                    self.log_files.append(df)
                    self.log_files_list.addItem(os.path.basename(file_name))
                except Exception as e:
                    QMessageBox.warning(self, "Warning", 
                        f"Failed to read {file_name}: {str(e)}")
            self.update_process_button()

    def add_condition(self):
        """Add a new condition"""
        condition_type = self.condition_type.text()
        threshold = self.threshold.value()
        if condition_type:
            condition = {"type": condition_type, "threshold": threshold}
            self.conditions.append(condition)
            self.conditions_list.addItem(
                f"{condition_type} - min Count: {threshold}")
            self.condition_type.clear()
            self.threshold.setValue(1)
            self.update_process_button()

    def update_process_button(self):
        """Update process button state"""
        self.process_button.setEnabled(
            self.list_file is not None and 
            len(self.log_files) > 0 and 
            len(self.conditions) > 0
        )

    def clean_number(self, phone):
        """Clean and standardize phone numbers"""
        phone = str(phone)
        phone = re.sub(r'\D', '', phone)
        if phone.startswith('1') and len(phone) > 10:
            phone = phone[1:]
        return phone

    def process_files(self):
        """Process the files"""
        try:
            QMessageBox.information(self, "Processing", "Processing files, please wait...")
            self.process_button.setEnabled(False)

            # Process files using your existing logic
            updated_list_df, updated_log_dfs, removed_log_records = self.process_data(
                self.log_files, 
                self.list_file,
                self.conditions, 
                [self.log_files_list.item(i).text() for i in range(self.log_files_list.count())]
            )

            # Upload to Google Drive
            current_date = datetime.now().strftime("%Y%m%d")
            
            # Upload updated list file
            list_io = BytesIO()
            updated_list_df.to_csv(list_io, index=False)
            list_io.seek(0)
            self.upload_to_drive(
                f"Updated_List_{current_date}.csv",
                list_io,
                self.REMOVED_FOLDER_ID
            )

            # Upload log files and removed records
            for i, log_df in enumerate(updated_log_dfs):
                log_name = self.log_files_list.item(i).text()
                
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
                if not removed_log_records[i].empty:
                    removed_io = BytesIO()
                    removed_log_records[i].to_csv(removed_io, index=False)
                    removed_io.seek(0)
                    self.upload_to_drive(
                        f"Removed_Records_{log_name}_{current_date}.csv",
                        removed_io,
                        self.REMOVED_FOLDER_ID
                    )

            # Create local zip file
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add updated list file
                list_csv = BytesIO()
                updated_list_df.to_csv(list_csv, index=False)
                list_csv.seek(0)
                zip_file.writestr(f"Updated_List_{current_date}.csv", list_csv.getvalue())

                # Add log files and their removed records
                for i, log_df in enumerate(updated_log_dfs):
                    log_name = self.log_files_list.item(i).text()
                    
                    # Add scrubbed log
                    log_csv = BytesIO()
                    log_df.to_csv(log_csv, index=False)
                    log_csv.seek(0)
                    zip_file.writestr(f"Scrubbed_{log_name}_{current_date}.csv", log_csv.getvalue())

                    # Add removed records if they exist
                    if not removed_log_records[i].empty:
                        removed_csv = BytesIO()
                        removed_log_records[i].to_csv(removed_csv, index=False)
                        removed_csv.seek(0)
                        zip_file.writestr(f"Removed_Records_{log_name}_{current_date}.csv", 
                                        removed_csv.getvalue())

            # Save zip file
            zip_buffer.seek(0)
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Processed Files", f"processed_files_{current_date}.zip", 
                "ZIP Files (*.zip)")
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(zip_buffer.getvalue())

            QMessageBox.information(self, "Success", 
                "Files processed and saved successfully!\nUploaded to Google Drive and saved locally.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Processing failed: {str(e)}")
        finally:
            self.process_button.setEnabled(True)

    def process_data(self, log_dfs, list_df, conditions, log_filenames):
        """Process the data"""
        # Normalize list file phone numbers
        list_df["Phone"] = list_df["Phone"].astype(str).apply(self.clean_number)

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

        # Parse conditions
        parsed_conditions = {cond["type"].title(): cond["threshold"] for cond in conditions}

        # Identify numbers to remove
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
                cleaned_phones_to_remove.extend([self.clean_number(phone) for phone in matching_numbers])

        # Process each log file
        for log_df, filename in zip(log_dfs, log_filenames):
            processed_log_df = log_df.copy()
            removed_records = pd.DataFrame()  # DataFrame for storing removed records

            # Normalize column names
            processed_log_df.columns = processed_log_df.columns.str.strip().str.lower()
            processed_log_df = processed_log_df.astype(str)

            # Identify potential phone number columns
            phone_columns = [
                col for col in processed_log_df.columns
                if any(phrase in col.lower() for phrase in ['mobile', 'phone', 'number', 'tel', 'contact', 'ph'])
            ]

            if not phone_columns:
                updated_log_dfs.append(processed_log_df)
                removed_log_records.append(pd.DataFrame())
                continue

            # Track which rows have had numbers removed
            rows_with_removed_numbers = set()

            # Process each phone column
            for col in phone_columns:
                # Clean the column's phone numbers
                processed_log_df[col] = processed_log_df[col].astype(str).apply(
                    lambda x: f"{int(float(x))}" if x.replace(".", "").isdigit() else x
                )
                original_values = processed_log_df[col].copy()
                cleaned_column = processed_log_df[col].apply(self.clean_number)

                # Identify rows to remove
                remove_mask = cleaned_column.isin(cleaned_phones_to_remove)

                if remove_mask.any():
                    # Store rows before clearing numbers
                    rows_with_removed_numbers.update(processed_log_df[remove_mask].index)
                    processed_log_df.loc[remove_mask, col] = ''

            # Create removed records DataFrame
            if rows_with_removed_numbers:
                removed_records = processed_log_df.loc[list(rows_with_removed_numbers)].copy()

            # Add processed DataFrames to lists
            updated_log_dfs.append(processed_log_df)
            removed_log_records.append(removed_records)

        return list_df, updated_log_dfs, removed_log_records


def main():
    app = QApplication(sys.argv)
    window = LogProcessorApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
