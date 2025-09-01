# Finance Manager

The backend system of a financial manager.


## How To Run It Locally

```bash
git clone git@github.com:henry-vg/Finance-Manager.git
cd Finance-Manager/
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "Insert .env content here" > .env
python3 main.py
```


## Folder Structure

```
Finance-Manager
├── logs                            
├── src                             
│   ├── adapters                    
│   │   ├── input                   
│   │   │   └── http                
│   │   │       ├── controllers     
│   │   │       ├── middlewares     
│   │   │       └── routers         
│   │   └── output                  
│   ├── core                        
│   │   ├── domain                  
│   │   ├── ports                   
│   │   │   ├── input               
│   │   │   └── output              
│   │   └── usecases                
│   └── infra                       
├── tests                           
│   ├── integration                 
│   ├── unit                        
├── main.py                         
└── settings.json                   
```