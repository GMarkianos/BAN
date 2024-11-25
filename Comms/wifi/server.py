import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate("/home/admin/Desktop/BAN/ban-net-firebase-adminsdk-xzaq7-e78cd98b2d.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://ban-net-rtdb.europe-west1.firebasedatabase.app/',
    'databaseAuthVariableOverride':{
        'sercret': 'rasp_sensor'
        }
        
    }) 

ref = db.reference('data')
ref.set({'Heartrate': 50, 'O2:':99})