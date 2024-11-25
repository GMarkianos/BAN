import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate("/home/admin/Desktop/BAN/Comms/ban-net-firebase-adminsdk-xzaq7-e78cd98b2d.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://ban-net-rtdb.europe-west1.firebasedatabase.app/'   
    })
    
try:
    ref = db.reference("/")
    data = ref.get()
    print("data",data)
except Exception as e:
    print("Error",e)
    
ref = db.reference('data')

try:
    ref.set({
        'Heartrate': 50,
        'O2': 99
    })
    print("ok")
except Exception as e:
    print(f"Error writing data: {e}")
