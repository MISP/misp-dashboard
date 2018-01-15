import sys,os,os.path
sys.path.insert(0, os.path.dirname(__file__))
os.environ["DASH_CONFIG"] = os.path.join(os.path.dirname(__file__), "config")
from server import app as application
