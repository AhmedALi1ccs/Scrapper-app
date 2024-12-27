import streamlit.web.bootstrap
import os
import sys

def run_app():
    # Get the directory containing the script
    if getattr(sys, 'frozen', False):
        # Running as a bundled executable
        app_dir = os.path.dirname(sys.executable)
    else:
        # Running as a script
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Point to your actual main app file
    main_script = os.path.join(app_dir, "your_main_app.py")
    
    # Set up Streamlit configuration
    os.environ["STREAMLIT_SERVER_PORT"] = "8501"
    os.environ["STREAMLIT_SERVER_ADDRESS"] = "localhost"
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_THEME_COLOR"] = "#FF4B75"  # Matches your button color
    os.environ["STREAMLIT_SERVER_MAX_UPLOAD_SIZE"] = "200"  # Set max upload size to 200MB
    os.environ["STREAMLIT_CLIENT_TOOLBAR_MODE"] = "minimal"  # Minimize toolbar
    os.environ["STREAMLIT_CLIENT_SHOW_TOOLBAR"] = "false"  # Hide toolbar
    os.environ["STREAMLIT_BROWSER_SERVER_PORT"] = "8501"  # Ensure consistent port
    os.environ["STREAMLIT_BROWSER_SERVER_ADDRESS"] = "localhost"  # Ensure localhost
    os.environ["STREAMLIT_SHARE_LOAD_SECRETS"] = "true"  # Enable secrets
    os.environ["STREAMLIT_GLOBAL_THREADING"] = "true"  # Enable threading
    os.environ["STREAMLIT_SERVER_ENABLE_STATIC_SERVING"] = "true"  # Enable static file serving
    os.environ["STREAMLIT_SERVER_BASE_URL"] = "/"  # Set base URL
    os.environ["STREAMLIT_BROWSER_ENABLE_XSRF_PROTECTION"] = "true"  # Enable XSRF protection
    os.environ["STREAMLIT_BROWSER_FILE_STORAGE_PATH"] = os.path.join(app_dir, "file_storage")  # Set file storage path
    
    # Create file storage directory if it doesn't exist
    file_storage_path = os.path.join(app_dir, "file_storage")
    if not os.path.exists(file_storage_path):
        os.makedirs(file_storage_path)
    
    # Ensure .env file is accessible
    env_path = os.path.join(app_dir, ".env")
    if os.path.exists(env_path):
        from dotenv import load_dotenv
        load_dotenv(env_path)
    
    # Launch the Streamlit app
    sys.argv = ["streamlit", "run", main_script]
    
    try:
        streamlit.web.bootstrap.run()
    except Exception as e:
        print(f"Error running Streamlit app: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")  # Keep window open on error
        sys.exit(1)

if __name__ == "__main__":
    try:
        run_app()
    except Exception as e:
        print(f"Failed to launch app: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")  # Keep window open on error
        sys.exit(1)