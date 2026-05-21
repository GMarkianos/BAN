from firebase_admin import credentials

cred = credentials.Certificate("/home/markiano/Desktop/ban-net-firebase-adminsdk-fbsvc-07cbbce9f5.json")
# for i in range(10):    
#     ref = db.reference("/")
#     ref.update({"O2" : hr +100})
#     ref.update({"hr": hr})
#     hr = hr + 10
#     time.sleep(1)
