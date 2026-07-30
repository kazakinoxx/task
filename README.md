## 1. Create and activate the experiment virtual environment (Python 3.10)
py -3.10 -m venv .venv310

.venv310\Scripts\activate      


## 2. Install experiment dependencies
pip install -r src2/requirements.txt

## 3. Run the experiment
python -m frontend.main --participant P01

settings can be changed on settings.json in src2/
