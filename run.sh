. ./DASHENV/bin/activate
./zmq_subscriber.py &
./zmq_dispatcher.py &
export FLASK_DEBUG=1
export FLASK_APP=server.py
flask run --host=0.0.0.0 --port=8001
