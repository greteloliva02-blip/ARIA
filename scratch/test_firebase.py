import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.firebase.firebase_client import init_firebase, save_message

def test():
    os.environ['FIREBASE_CRED_PATH'] = r'C:\ARIA\services\firebase\service_account.json'
    os.environ['FIREBASE_PROJECT_ID'] = 'aria-872ca'
    db = init_firebase()
    if db is None:
        print('Firebase init failed')
        return
    success = save_message('test_user', 'assistant', 'Hello from test', __import__('datetime').datetime.utcnow())
    print('Save result:', success)

if __name__ == '__main__':
    test()
