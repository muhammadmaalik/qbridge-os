from pyngrok import ngrok, conf
import time

def start_tunnel():
    print("\n[!] Ngrok has recently disabled anonymous tunnels.")
    print("To secure your tunnel, please input your free Authtoken.")
    print("You can get it instantly by logging in at: https://dashboard.ngrok.com/get-started/your-authtoken")
    
    auth_token = input("\nPaste your Ngrok Authtoken here: ").strip()
    
    if auth_token:
        conf.get_default().auth_token = auth_token
        print("Authtoken configured! Starting secure tunnel...")
    else:
        print("No token provided. Attempting to run anyway (this may fail)...")

    try:
        tunnel = ngrok.connect(8000)
        print("\n" + "="*60)
        print(">>> SUCCESS! GLOBAL ACCESS ACTIVATED <<<")
        print(f"AxesQ Platform is now LIVE at: {tunnel.public_url}")
        print("="*60 + "\n")
        print("Keep this terminal open to maintain the connection.")
        print("Press Ctrl+C to close the tunnel.")
        
        # Keep the python process running indefinitely
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down tunnel...")
        ngrok.kill()
    except Exception as e:
        print(f"\nFailed to build tunnel. Error: {e}")

if __name__ == "__main__":
    start_tunnel()
