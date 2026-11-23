"""Seed realistic data through the public API (as an admin) for the UI walkthrough."""
import httpx, sys
B="http://127.0.0.1:8000/api"
c=httpx.Client(base_url=B)
r=c.post("/auth/login",json={"identifier":"super@example.org","password":"Sabha-admin-2026"}); r.raise_for_status()
h={"Authorization":f"Bearer {r.json()['access_token']}"}
r=c.post("/super-admin/admins",headers=h,json={"full_name":"P. Lakshmi Narayana","email":"office.admin@example.org","phone":"9000000002","temporary_password":"Office-admin-2026"}); print("admin",r.status_code)
people=[("1001","Sri Subramanyam Chetty","Sri Venkatachalam Chetty","Chennai","9840012345","Kasyapa","B+"),
("1002","T. Raghavendra Rao","T. Narasimha Rao","Chennai","9840012346","Bharadwaja","O+"),
("1003","K. Padmavathi","K. Sambasiva Rao","Vellore","9840012347","Vasishta","A+"),
("1004","M. Venkateswarlu","M. Ramaiah","Nellore","9840012348","Kaundinya","AB+"),
("1005","S. Annapurna","S. Gopalakrishna","Kanchipuram","9840012349","Atreya","B-"),
("1006","G. Chandrasekhar","G. Subba Rao","Tiruvallur","9840012350","Harita","O-")]
for num,name,father,city,cell,goth,bg in people:
    r=c.post("/admin/members",headers=h,json={"membership_number":num,"full_name":name,"father_name":father,"address_line1":"No. 4, Kalappachari Street","city":city,"state":"Tamil Nadu","country":"India","pincode":"600003","date_of_birth":"1962-03-10","cell":cell,"gothram":goth,"blood_group":bg,"occupation":"Merchant","family_surname":name.split()[0].strip('.'),"natchathiram":"Rohini","native_place_address":"Nellore District, Andhra Pradesh","enrolled_on":"1998-04-14","verified_by":"Office","receipt_number":f"R-{num}"})
    print(num,r.status_code, r.text[:120] if r.status_code>=300 else "")
r=c.put("/super-admin/settings/membership-sequence",headers=h,json={"next_value":1007}); print("seq",r.json()["examples"])
