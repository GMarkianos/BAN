import firebase_admin
from firebase_admin import credentials, db
import time

cred = credentials.Certificate("/home/admin/Desktop/ban-net-firebase-adminsdk-xzaq7-e78cd98b2d.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://ban-net-default-rtdb.europe-west1.firebasedatabase.app/"   
    })
    
ref = db.reference("/")

ref.update({"hr": 100})

time.sleep(1)
