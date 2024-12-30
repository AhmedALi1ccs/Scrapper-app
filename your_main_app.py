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
import json
from dotenv import load_dotenv

class LogProcessorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Log Processor")
        self.setMinimumSize(1200, 900)  # Increased window size
        self.setContentsMargins(30, 30, 30, 30)  # Increased margins

        # Initialize variables
        self.list_file = None
        self.log_files = []
        self.conditions = []
        
        # Load environment variables
        load_dotenv()
        
        # Create main widget with padding
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(30, 30, 30, 30)  # Increased margins
        layout.setSpacing(25)  # Increased spacing between elements

        # Add title with more space
        title_label = QLabel("Log File Processor")
        title_label.setStyleSheet("""
            font-size: 28px;
            color: #1976D2;
            font-weight: bold;
            margin: 20px 0;
            padding: 10px;
        """)
        layout.addWidget(title_label)
        layout.addSpacing(20)  # Add space after title

        # Create progress section first (needed for status updates)
        self.create_progress_section(layout)
        layout.addSpacing(30)
        
        # Create all UI sections
        self.create_upload_section(layout)
        layout.addSpacing(30)
        self.create_conditions_section(layout)
        layout.addSpacing(30)
        self.create_process_button(layout)

        # Style the UI
        self.style_ui()

        # Google Drive settings - now using environment variables
        self.REMOVED_FOLDER_ID = "18evx04gWua9ls1mDiIr5FvAQhdFbrwfr"
        self.SCRUBBED_FOLDER_ID = "1-jYrCY5ev44Hy5fXVwOZSjw7xPSTy9ML"
        
        # Initialize Google Drive service
        self.service = None
        QTimer.singleShot(0, self.initialize_drive_service)
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
                padding: 15px 25px;
                border-radius: 8px;
                min-width: 150px;
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
                font-size: 15px;
                color: #2c3e50;
                font-weight: bold;
                margin: 10px 0;
            }
            
            QListWidget {
                border: 2px solid #e8e8e8;
                border-radius: 8px;
                padding: 10px;
                background-color: white;
                min-height: 200px;
            }
            
            QListWidget::item {
                padding: 10px;
                border-radius: 4px;
                margin: 3px 0;
            }
            
            QListWidget::item:hover {
                background-color: #f0f0f0;
            }
            
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976D2;
            }
            
            QLineEdit {
                padding: 12px;
                border: 2px solid #e8e8e8;
                border-radius: 8px;
                background-color: white;
                font-size: 14px;
            }
            
            QLineEdit:focus {
                border-color: #2196F3;
            }
            
            QSpinBox {
                padding: 12px;
                border: 2px solid #e8e8e8;
                border-radius: 8px;
                background-color: white;
                font-size: 14px;
                min-width: 100px;
            }
            
            QSpinBox:focus {
                border-color: #2196F3;
            }

            QTextEdit {
                font-size: 14px;
                padding: 10px;
            }
        """)

    def create_progress_section(self, layout):
        """Create progress tracking section"""
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(10, 10, 10, 10)
        progress_layout.setSpacing(15)

        # Progress header
        header = QLabel("Progress")
        header.setStyleSheet("""
            font-size: 20px;
            color: #1976D2;
            font-weight: bold;
            padding: 10px 0;
        """)
        progress_layout.addWidget(header)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e8e8e8;
                border-radius: 8px;
                text-align: center;
                height: 30px;
                font-size: 14px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 6px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        # Status updates text area
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMinimumHeight(150)
        self.status_text.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e8e8e8;
                border-radius: 8px;
                padding: 10px;
                background-color: white;
                font-family: Arial;
            }
        """)
        progress_layout.addWidget(self.status_text)

        layout.addWidget(progress_container)

    def create_upload_section(self, layout):
        """Create the file upload section"""
        upload_container = QWidget()
        upload_layout = QVBoxLayout(upload_container)
        upload_layout.setContentsMargins(10, 10, 10, 10)
        upload_layout.setSpacing(20)
        
        header = QLabel("File Upload")
        header.setStyleSheet("""
            font-size: 20px;
            color: #1976D2;
            font-weight: bold;
            padding: 10px 0;
        """)
        upload_layout.addWidget(header)

        # List file section
        list_section = QWidget()
        list_layout = QVBoxLayout(list_section)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(10)
        
        list_label = QLabel("List File (CSV):")
        self.list_file_label = QLabel("No file selected")
        self.list_file_label.setStyleSheet("color: #666; font-weight: normal;")
        
        list_button = QPushButton("Choose List File")
        list_button.clicked.connect(self.upload_list_file)
        
        list_layout.addWidget(list_label)
        list_layout.addWidget(list_button)
        list_layout.addWidget(self.list_file_label)
        
        upload_layout.addWidget(list_section)
        upload_layout.addSpacing(20)

        # Log files section
        log_section = QWidget()
        log_layout = QVBoxLayout(log_section)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(10)
        
        log_label = QLabel("Log Files (CSV):")
        log_button = QPushButton("Choose Log Files")
        log_button.clicked.connect(self.upload_log_files)
        
        self.log_files_list = QListWidget()
        self.log_files_list.setMinimumHeight(250)  # Increased height
        
        log_layout.addWidget(log_label)
        log_layout.addWidget(log_button)
        log_layout.addWidget(self.log_files_list)
        
        upload_layout.addWidget(log_section)
        layout.addWidget(upload_container)
    def create_conditions_section(self, layout):
        """Create the conditions section"""
        conditions_container = QWidget()
        conditions_layout = QVBoxLayout(conditions_container)
        conditions_layout.setContentsMargins(10, 10, 10, 10)
        conditions_layout.setSpacing(20)
        
        header = QLabel("Conditions")
        header.setStyleSheet("""
            font-size: 20px;
            color: #1976D2;
            font-weight: bold;
            padding: 10px 0;
        """)
        conditions_layout.addWidget(header)

        # Input section
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(15)
        
        self.condition_type = QLineEdit()
        self.condition_type.setPlaceholderText("Enter Condition Type")
        self.condition_type.setMinimumWidth(300)
        
        self.threshold = QSpinBox()
        self.threshold.setMinimum(1)
        self.threshold.setMaximum(9999)
        self.threshold.setValue(1)
        
        add_condition_button = QPushButton("Add Condition")
        add_condition_button.clicked.connect(self.add_condition)
        
        input_layout.addWidget(self.condition_type, stretch=2)
        input_layout.addWidget(self.threshold, stretch=1)
        input_layout.addWidget(add_condition_button, stretch=1)
        
        conditions_layout.addWidget(input_widget)

        # Added conditions list
        conditions_label = QLabel("Added Conditions:")
        conditions_label.setStyleSheet("""
            font-size: 15px;
            margin-top: 15px;
        """)
        conditions_layout.addWidget(conditions_label)
        
        self.conditions_list = QListWidget()
        self.conditions_list.setMinimumHeight(150)
        conditions_layout.addWidget(self.conditions_list)
        
        layout.addWidget(conditions_container)

    def create_process_button(self, layout):
        """Create the process button"""
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(10, 20, 10, 20)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.process_button = QPushButton("Process Files")
        self.process_button.clicked.connect(self.process_files)
        self.process_button.setEnabled(False)
        self.process_button.setMinimumHeight(60)
        self.process_button.setMinimumWidth(200)
        self.process_button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                background-color: #2196F3;
                padding: 15px 30px;
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
        """)
        
        button_layout.addWidget(self.process_button)
        layout.addWidget(button_container)

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

    def add_condition(self):
        """Add a new condition"""
        condition_type = self.condition_type.text().strip()
        threshold = self.threshold.value()
        if condition_type:
            condition = {"type": condition_type, "threshold": threshold}
            self.conditions.append(condition)
            self.conditions_list.addItem(
                f"{condition_type} - min Count: {threshold}")
            self.condition_type.clear()
            self.threshold.setValue(1)
            self.update_status(f"Added condition: {condition_type} with threshold {threshold}")
            self.update_process_button()
        else:
            QMessageBox.warning(self, "Warning", "Please enter a condition type")

    def update_process_button(self):
        """Update process button state"""
        can_process = (
            self.list_file is not None and 
            len(self.log_files) > 0 and 
            len(self.conditions) > 0
        )
        self.process_button.setEnabled(can_process)
        if can_process:
            self.update_status("Ready to process files")
    def authenticate(self):
        """Authenticate Google Drive API"""
        try:
            # Get credentials from environment variable
            credentials_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
            if not credentials_json_str:
                self.update_status("Error: No Google credentials found in environment")
                return None

            try:
                credentials_json = json.loads(credentials_json_str)
            except json.JSONDecodeError:
                self.update_status("Error: Invalid Google credentials format")
                return None

            creds = Credentials.from_service_account_info(
                credentials_json, 
                scopes=['https://www.googleapis.com/auth/drive']
            )
            
            service = build('drive', 'v3', credentials=creds)
            return service

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

    def upload_list_file(self):
        """Handle list file upload"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select List File", "", "CSV Files (*.csv)")
        if file_name:
            try:
                encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
                for encoding in encodings:
                    try:
                        df = pd.read_csv(file_name, encoding=encoding)
                        # Replace NaN values with empty strings
                        df = df.fillna('').replace(['nan', 'NaN', 'NaT'], '')
                        self.list_file = df
                        self.list_file_label.setText(os.path.basename(file_name))
                        self.update_status(f"Successfully loaded list file: {os.path.basename(file_name)}")
                        self.update_process_button()
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    QMessageBox.critical(self, "Error", "Could not read file with any supported encoding")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read file: {str(e)}")

    def upload_log_files(self):
        """Handle log files upload"""
        file_names, _ = QFileDialog.getOpenFileNames(
            self, "Select Log Files", "", "CSV Files (*.csv)")
        if file_names:
            self.log_files = []
            self.log_files_list.clear()
            total_files = len(file_names)
            
            for i, file_name in enumerate(file_names, 1):
                encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
                for encoding in encodings:
                    try:
                        df = pd.read_csv(file_name, encoding=encoding)
                        # Replace NaN values with empty strings
                        df = df.fillna('').replace(['nan', 'NaN', 'NaT'], '')
                        self.log_files.append(df)
                        self.log_files_list.addItem(os.path.basename(file_name))
                        self.update_status(f"Loaded log file ({i}/{total_files}): {os.path.basename(file_name)}")
                        progress = (i / total_files) * 100
                        self.progress_bar.setValue(progress)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    QMessageBox.warning(self, "Warning", 
                        f"Failed to read {file_name} with any supported encoding")
            
            self.progress_bar.setValue(0)
            self.update_process_button()

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


def main():
    app = QApplication(sys.argv)
    window = LogProcessorApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
