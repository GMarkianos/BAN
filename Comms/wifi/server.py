import firebase_admin
from firebase_admin import credentials, db
import time

cred = credentials.Certificate("/home/markiano/Desktop/ban-net-firebase-adminsdk-fbsvc-07cbbce9f5.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://ban-net-default-rtdb.europe-west1.firebasedatabase.app/"   
    })
    hr = 10
# for i in range(10):    
#     ref = db.reference("/")
#     ref.update({"O2" : hr +100})
#     ref.update({"hr": hr})
#     hr = hr + 10
#     time.sleep(1)
