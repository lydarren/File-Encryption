

import os
import base64
import cryptography
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding, serialization, hashes, hmac
from cryptography.hazmat.primitives.asymmetric import rsa
import cryptography.hazmat.primitives.asymmetric as asymm

def MyencryptMAC(message, key, HMACKey):
    if(not isinstance(message, bytes)):
        m = bytes(message, "utf-8")
    else:
        m = message
        
    padder = padding.PKCS7(128).padder()
    m = padder.update(m) + padder.finalize()

    if(len(key) < 32):
        print("The key size is too small!!")
    else:
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())

        encryptor = cipher.encryptor()
        ct = encryptor.update(m) + encryptor.finalize()
        
        h = hmac.HMAC(HMACKey, hashes.SHA256(), backend=default_backend())
        h.update(ct)
        tag = h.finalize()
        #iv ciphertext and hashtag
        return iv, ct, tag
    

def MydecryptMAC(C, iv, key, hKey, tag):
    backend = default_backend()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
    decryptor = cipher.decryptor()
    m = decryptor.update(C) + decryptor.finalize()
        
    try:
        h = hmac.HMAC(hKey, hashes.SHA256(), backend=default_backend())
        h.update(C)
        h.verify(tag)
        unpadder = padding.PKCS7(128).unpadder()
        mData = unpadder.update(m)
        mData += unpadder.finalize()
        return mData.decode("utf-8")
    except cryptography.exceptions.InvalidSignature:
        print("Signature does not match")
        
    return m.decode("utf-8")


def MyfileEncryptMAC(filePath):
    # getting the path of the image
    imgKey = os.urandom(32)
    path = filePath
    # getting the extension for the img
    filePath, ext = os.path.splitext(path) 
    # converts the image to a string
    with open(path, "rb") as file:
        imgStr = base64.b64encode(file.read()) # string is in bytes

    # encrypting image string
    HMACKey = os.urandom(32)
    iv, c, tag = MyencryptMAC(imgStr, imgKey, HMACKey)

    # converts an encrypted img string into an image
    """
    encFile = filePath#  + ext
    with open(encFile, 'wb') as file:
        file.write(c)
        file.close()
    """
    return c, iv, imgKey, ext, HMACKey, tag
    

def MyfileDecryptMAC(C, IV, key, fileName, ext, hKey, tag):
    unEncFile = fileName + ext
    # decrypts the image string from the encrypted image
    dImgStr = MydecryptMAC(C, IV, key, hKey, tag)
    #converts decrypted image str into an image
    imageData = base64.b64decode(dImgStr)
    with open(unEncFile, 'wb') as file:
        file.write(imageData)
        file.close()



def MyRSAEncrypt(filepath, RSA_Publickey_filepath):
    #encrypt file to get the key
    C, IV, key, ext, hKey, tag = MyfileEncryptMAC(filepath)
    
    #load the public key
    with open(RSA_Publickey_filepath, "rb") as key_file:
        public_key = serialization.load_pem_public_key(
                key_file.read(),
                backend=default_backend()
                )
    #encrypt the key to get RSACipher
    RSACipher = public_key.encrypt(
            key + hKey, 
            asymm.padding.OAEP(
                    mgf=asymm.padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None 
                    )
            )
    
    return RSACipher, C, IV, ext, tag
    
    
def MyRSADecrypt(RSACipher, C, IV, filepath, ext, RSA_Privatekey_filepath, tag):
    #load private key
    with open(RSA_Privatekey_filepath, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
                backend=default_backend())
        
    #decrypt the RSACipher to get the key
    key = private_key.decrypt(
        RSACipher,
        asymm.padding.OAEP(
                mgf=asymm.padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
        )
    )
    #decrypt using original key
    k = key[0:32]
    hKey = key[len(k):]
    MyfileDecryptMAC(C, IV, k, filepath, ext, hKey, tag)
        

def generateKeys():
    #check if key folder exists
    folder = "keys"
    privkey_name = "private_key.pem"
    pubkey_name = "public_key.pem"
    files = os.listdir()
    if folder not in files:
        #create keys folder
        os.mkdir(folder)
        
    #os.chdir(folder)
    #check if keys exist
    files = os.listdir(folder)
    priv_exist = privkey_name in files
    pub_exist = pubkey_name in files
    #keys dont exist
    if priv_exist is True and pub_exist is True:
        print("Keys have been found!!")
        return True
    
    # key info(
    key = rsa.generate_private_key(
            backend=default_backend(), 
            public_exponent=65537,
            key_size=2048)
    # private key
    private_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
            )
    #write private key to file
    with open(folder + "\\" + privkey_name, 'wb') as file:
        file.write(private_pem)
        file.close()
    
    #create a public key
    public = key.public_key()
    public_pem = public.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
    #write pub key to file
    with open(folder + "\\" + pubkey_name, 'wb') as file:
        file.write(public_pem)
        file.close()
    print("Keys have been created!!")
    return False
    
	
def startEncrypt():
    files = os.listdir()
    
    if "keys" in files:
        files.remove("keys")
    if "FileEncryptMac.exe" in files:
        files.remove("FileEncryptMac.exe")
        
    for file_name in files:
        print("Encrypting " + file_name + "...") 
        RSACipher, C, IV, ext, tag = MyRSAEncrypt(file_name, "keys/public_key.pem")        	
    
        fname = os.path.splitext(str(file_name))[0]
        #decode into latin-1 to write to json (utf-8 doesnt work)
        js = {
            "RSACipher": RSACipher.decode('latin-1'),
            "C": C.decode('latin-1'),
            "IV": IV.decode('latin-1'),
            "ext": ext,
            "tag": tag.decode('latin-1')     
        }         
        #store in json file 
        with open(fname + '.json', 'w') as outfile:
            json.dump(js, outfile, indent=4)
        #remove original files
        os.remove(file_name)
    		
def startDecrypt():	
    files = os.listdir()
    
    if "keys" in files:
        files.remove("keys")
    if "FileEncryptMac.exe" in files:
        files.remove("FileEncryptMac.exe")

    for file_name in files:     
        #opens the json file
        with open(file_name, 'r') as re:
            s = json.load(re)
        #get filename w/e extension
        fname = os.path.splitext(str(file_name))[0]
        
        print("Decrypting " + file_name + "...")
        #encrypted file data
        xRSACipher = bytes(s["RSACipher"], 'latin-1')
        xC = bytes(s["C"], 'latin-1')
        xIV = bytes(s["IV"], 'latin-1')
        xExt = s["ext"]
        xTag = bytes(s["tag"], 'latin-1')
        MyRSADecrypt(xRSACipher, xC, xIV, fname, xExt, "keys/private_key.pem", xTag)
        #remove json files
        os.remove(file_name)

import time

generateKeys()
startEncrypt()
time.sleep(5)
startDecrypt()
time.sleep(5)
