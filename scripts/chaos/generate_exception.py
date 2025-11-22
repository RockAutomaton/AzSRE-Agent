import logging
import os
import sys
import time
import threading
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Try to import the Azure exporter, handle if missing
try:
    from opencensus.ext.azure.log_exporter import AzureLogHandler
except ImportError:
    print("❌ Error: 'opencensus-ext-azure' is not installed.")
    print("Please run: uv sync")
    sys.exit(1)


def telemetry_processor(envelope):
    """
    Callback to modify the telemetry envelope before sending.
    Sets the Cloud Role Name to 'nuffin' to match our alert rules.
    """
    envelope.tags['ai.cloud.role'] = 'nuffin'
    return True


def trigger_exception():
    # 1. Get Connection String
    conn_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    
    if not conn_string:
        print("❌ Error: APPLICATIONINSIGHTS_CONNECTION_STRING environment variable is not set.")
        print("Export it in your terminal:")
        print('export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=..."')
        sys.exit(1)

    print(f"🔌 Connecting to Application Insights as role 'nuffin'...")

    # 2. Configure Logger
    # Use a unique logger name to avoid conflicts
    logger = logging.getLogger(f"nuffin_chaos_logger_{id(conn_string)}")
    logger.setLevel(logging.ERROR)  # Only log Errors and Criticals
    
    # Clear any existing handlers to avoid conflicts
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    logger.propagate = False  # Prevent propagation to root logger
    
    # Attach the Azure Exporter
    azure_handler = AzureLogHandler(connection_string=conn_string)
    
    # Fix: Manually initialize the lock if it's None (known issue with opencensus-ext-azure)
    if not hasattr(azure_handler, 'lock') or azure_handler.lock is None:
        azure_handler.lock = threading.Lock()
    
    # Register the callback to set the Role Name BEFORE adding to logger
    azure_handler.add_telemetry_processor(telemetry_processor)
    
    # Ensure handler is properly initialized
    azure_handler.setLevel(logging.ERROR)
    
    logger.addHandler(azure_handler)

    # 3. Simulate a Crash
    print("⚠️  Simulating a critical application crash...")
    
    try:
        # The "Business Logic" that fails
        numerator = 42
        denominator = 0
        _ = numerator / denominator
    except ZeroDivisionError:
        # 4. Capture and Send
        print("💥 Exception caught! Sending telemetry to Azure...")
        
        try:
            # 'logger.exception' automatically includes the stack trace in the log
            logger.exception(
                "Simulated Failure: Calculation Engine Crash", 
                extra={'custom_dimensions': {'Simulation': 'True', 'User': 'ChaosScript'}}
            )
            
            # Give the handler time to process the log
            time.sleep(1)
            
            # Important: Flush ensures data is sent before script exits
            # The SDK usually buffers, so we force it out.
            for handler in logger.handlers:
                if isinstance(handler, AzureLogHandler):
                    try:
                        handler.flush()
                    except Exception as e:
                        print(f"⚠️  Warning: Could not flush handler: {e}")
            
            # Give a bit more time for the flush to complete
            time.sleep(0.5)
            
            print("✅ Exception sent. Check 'AppExceptions' in Azure Monitor in ~2-5 minutes.")
        except Exception as e:
            print(f"❌ Error sending exception: {e}")
            raise
        finally:
            # Clean up handlers
            for handler in logger.handlers[:]:
                try:
                    handler.close()
                    logger.removeHandler(handler)
                except Exception:
                    pass


if __name__ == "__main__":
    trigger_exception()

