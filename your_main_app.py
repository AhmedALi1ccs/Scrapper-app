import sys
import os
import pandas as pd
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QPushButton, QLabel, QFileDialog, QListWidget, QSpinBox, QHBoxLayout,
    QLineEdit, QMessageBox, QProgressBar, QTextEdit)
from PyQt6.QtCore import Qt, QTimer
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO
import zipfile
from datetime import datetime

class LogProcessorApp(QMainWindow):
    class LogProcessorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Log Processor")
        self.setMinimumSize(1000, 800)
        self.setContentsMargins(20, 20, 20, 20)

        # Initialize variables
        self.list_file = None
        self.log_files = []
        self.conditions = []
        
        # Create main widget with padding
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Add title
        title_label = QLabel("Log File Processor")
        title_label.setStyleSheet("""
            font-size: 24px;
            color: #1976D2;
            font-weight: bold;
            margin-bottom: 20px;
        """)
        layout.addWidget(title_label)

        # Create all UI sections first
        self.create_upload_section(layout)
        layout.addSpacing(20)
        self.create_conditions_section(layout)
        layout.addSpacing(20)
        self.create_progress_section(layout)
        layout.addSpacing(20)
        self.create_process_button(layout)

        # Style the UI
        self.style_ui()

        # Google Drive settings - moved to after UI initialization
        self.REMOVED_FOLDER_ID = "18evx04gWua9ls1mDiIr5FvAQhdFbrwfr"
        self.SCRUBBED_FOLDER_ID = "1-jYrCY5ev44Hy5fXVwOZSjw7xPSTy9ML"
        
        # Initialize Google Drive service
        self.service = None
        QTimer.singleShot(0, self.initialize_drive_service)

    def initialize_drive_service(self):
        """Initialize Google Drive service after UI is ready"""
        try:
            self.service = self.authenticate()
            if self.service:
                self.update_status("Google Drive authentication successful")
            else:
                self.update_status("Failed to authenticate with Google Drive")
        except Exception as e:
            self.update_status(f"Error initializing Google Drive: {str(e)}")

    def create_progress_section(self, layout):
        """Create progress tracking section"""
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)

        # Progress header
        header = QLabel("Progress")
        header.setStyleSheet("""
            font-size: 18px;
            color: #1976D2;
            font-weight: bold;
            padding-bottom: 10px;
        """)
        progress_layout.addWidget(header)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e8e8e8;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        # Status updates text area
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMinimumHeight(100)
        self.status_text.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e8e8e8;
                border-radius: 8px;
                padding: 10px;
                background-color: white;
            }
        """)
        progress_layout.addWidget(self.status_text)

        layout.addWidget(progress_container)

    def update_status(self, message, progress=None):
        """Update status text and progress bar"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )
        if progress is not None:
            self.progress_bar.setValue(progress)
        QApplication.processEvents()

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
        """)

    def create_upload_section(self, layout):
        """Create the file upload section"""
        upload_container = QWidget()
        upload_layout = QVBoxLayout(upload_container)
        upload_layout.setContentsMargins(0, 0, 0, 0)
        
        header = QLabel("File Upload")
        header.setStyleSheet("""
            font-size: 18px;
            color: #1976D2;
            font-weight: bold;
            padding-bottom: 10px;
        """)
        upload_layout.addWidget(header)

        # List file section
        list_section = QWidget()
        list_layout = QVBoxLayout(list_section)
        list_layout.setContentsMargins(0, 0, 0, 0)
        
        list_label = QLabel("List File (CSV):")
        list_button = QPushButton("Choose List File")
        list_button.clicked.connect(self.upload_list_file)
        
        self.list_file_label = QLabel("No file selected")
        self.list_file_label.setStyleSheet("color: #666; font-weight: normal;")
        
        list_layout.addWidget(list_label)
        list_layout.addWidget(list_button)
        list_layout.addWidget(self.list_file_label)
        
        upload_layout.addWidget(list_section)
        upload_layout.addSpacing(15)

        # Log files section
        log_section = QWidget()
        log_layout = QVBoxLayout(log_section)
        log_layout.setContentsMargins(0, 0, 0, 0)
        
        log_label = QLabel("Log Files (CSV):")
        log_button = QPushButton("Choose Log Files")
        log_button.clicked.connect(self.upload_log_files)
        
        self.log_files_list = QListWidget()
        self.log_files_list.setMinimumHeight(150)
        
        log_layout.addWidget(log_label)
        log_layout.addWidget(log_button)
        log_layout.addWidget(self.log_files_list)
        
        upload_layout.addWidget(log_section)
        layout.addWidget(upload_container)

    def create_conditions_section(self, layout):
        """Create the conditions section"""
        conditions_container = QWidget()
        conditions_layout = QVBoxLayout(conditions_container)
        conditions_layout.setContentsMargins(0, 0, 0, 0)
        
        header = QLabel("Conditions")
        header.setStyleSheet("""
            font-size: 18px;
            color: #1976D2;
            font-weight: bold;
            padding-bottom: 10px;
        """)
        conditions_layout.addWidget(header)

        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.condition_type = QLineEdit()
        self.condition_type.setPlaceholderText("Enter Condition Type")
        
        self.threshold = QSpinBox()
        self.threshold.setMinimum(1)
        self.threshold.setFixedWidth(100)
        
        add_condition_button = QPushButton("Add Condition")
        add_condition_button.clicked.connect(self.add_condition)
        
        input_layout.addWidget(self.condition_type, stretch=2)
        input_layout.addWidget(self.threshold, stretch=1)
        input_layout.addWidget(add_condition_button, stretch=1)
        
        conditions_layout.addWidget(input_widget)

        conditions_label = QLabel("Added Conditions:")
        conditions_label.setStyleSheet("margin-top: 15px;")
        conditions_layout.addWidget(conditions_label)
        
        self.conditions_list = QListWidget()
        self.conditions_list.setMinimumHeight(100)
        conditions_layout.addWidget(self.conditions_list)
        
        layout.addWidget(conditions_container)

    def create_process_button(self, layout):
        """Create the process button"""
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.process_button = QPushButton("Process Files")
        self.process_button.clicked.connect(self.process_files)
        self.process_button.setEnabled(False)
        self.process_button.setMinimumHeight(50)
        self.process_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
            }
        """)
        
        button_layout.addWidget(self.process_button)
        layout.addWidget(button_container)

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
                "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/python-api%40fluent-vortex-441616-c0.iam.gserviceaccount.com",
                "universe_domain": "googleapis.com"
            }
    
            # Add proper error checking
            if not credentials_json.get("private_key"):
                self.update_status("Error: Invalid private key in credentials")
                return None
                
            creds = Credentials.from_service_account_info(
                credentials_json, 
                scopes=['https://www.googleapis.com/auth/drive']
            )
            
            service = build('drive', 'v3', credentials=creds)
            # Test the connection
            try:
                service.files().list(pageSize=1).execute()
                return service
            except Exception as e:
                self.update_status(f"Drive API test failed: {str(e)}")
                return None
                
        except Exception as e:
            self.update_status(f"Authentication failed: {str(e)}")
            return None

    def upload_to_drive(self, file_name, file_data, folder_id):
        """Upload a file to Google Drive"""
        try:
            self.update_status(f"Uploading {file_name} to Google Drive...")
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
            self.update_status(f"Successfully uploaded {file_name}")
            return file.get('id')
        except Exception as e:
            self.update_status(f"Failed to upload {file_name}: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to upload {file_name}: {str(e)}")
            return None

    def process_data(self, log_dfs, list_df, conditions, log_filenames):
        """Process the data using conditions"""
        try:
            self.update_status("Starting data processing...")
            self.progress_bar.setValue(10)

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
            removed_from_list = pd.DataFrame()
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
                    current_removed = list_df[list_df["Phone"].isin(matching_numbers)]
                    removed_from_list = pd.concat([removed_from_list, current_removed])
                    list_df = list_df[~list_df["Phone"].isin(matching_numbers)]
                    cleaned_phones_to_remove.extend([self.clean_number(phone) for phone in matching_numbers])
                    self.update_status(f"Found {len(matching_numbers)} numbers matching condition: {cond_type}")

            self.progress_bar.setValue(50)

            # Process each log file
            total_logs = len(log_dfs)
            for i, (log_df, filename) in enumerate(zip(log_dfs, log_filenames), 1):
                self.update_status(f"Processing log file {i}/{total_logs}: {filename}")
                
                processed_log_df = log_df.copy()
                removed_records = pd.DataFrame()

                # Normalize column names
                processed_log_df.columns = processed_log_df.columns.str.strip().str.lower()
                processed_log_df = processed_log_df.astype(str)

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
                        rows_with_removed_numbers.update(processed_log_df[remove_mask].index)
                        self.update_status(f"Found {remove_mask.sum()} numbers to remove in {col}")
                        processed_log_df.loc[remove_mask, col] = ''

                # Create removed records DataFrame
                if rows_with_removed_numbers:
                    removed_records = processed_log_df.loc[list(rows_with_removed_numbers)].copy()
                    self.update_status(f"Created removed records for {filename}")

                updated_log_dfs.append(processed_log_df)
                removed_log_records.append(removed_records)

                progress = 50 + (i / total_logs * 40)  # Progress from 50% to 90%
                self.progress_bar.setValue(progress)

            self.progress_bar.setValue(100)
            self.update_status("Data processing completed successfully!")
            return list_df, updated_log_dfs, removed_log_records

        except Exception as e:
            self.update_status(f"Error processing data: {str(e)}")
            raise e


def main():
    app = QApplication(sys.argv)
    window = LogProcessorApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
