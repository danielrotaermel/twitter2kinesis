# twitter2kinesis

A flask server that streams tweets from the twitter streaming api to AWS Kinesis, thanks to [@brennv](https://github.com/brennv/flask-ansible-example) it's ready to be deployed with a simplified Ansible playbook. Also there is a site.yml included that will deal wit the creation of a ec2 instance. Change the ami to your prefered distribution.

The included deploy playbook will:
- Install system apt packages
- Clone the repo and install Python requirements in a virtualenv
- Configure gunicorn, nginx, ufw and systemd
- Enable and start services
- Check the url for the expected response

The `deploy.yml` playbook is modeled after the manual steps discussed in this [digitalocean article](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-16-04)

## Prerequisites

You'll need [Ansible installed](https://docs.ansible.com/ansible/latest/intro_installation.html) and SSH access to any hosts. Customize the `.hosts` file as needed.

```
pip install ansible
git clone https://github.com/brennv/flask-ansible-example.git
cd flask-ansible-example
nano .hosts
```

## Deploying the app

Run the deploy playbook.
```
ansible-playbook deploy.yml
```

## Debugging

Test connection with the host. If needed, configure the ssh agent.
```
ansible webservers -m ping
ssh-add ~/.ssh/example_rsa
```

Rerun the playbook with verbosity.
```
ansible-playbook deploy.yml -vvvv
```

Check the logs on the host.
```
journalctl -xe
journalctl -u nginx
journalctl -u twitter2kinesis
```

Check the systemd status of the services on the host.
```
sudo systemctl status nginx
sudo systemctl status twitter2kinesis.service
```

Test the app.
```
sudo ufw allow 5000  # to undo: sudo ufw delete allow 5000
source env/bin/activate
python app.py
open http://HOSTNAME:5000
```
If that doesn't work, try running the Flask app with `app.run(debug=True)`

Test gunicorn.
```
gunicorn --bind 0.0.0.0:5000 wsgi:app
```

Test gunicorn in debug mode.
```
gunicorn --log-level debug --error-logfile error.log \
    --bind 0.0.0.0:5000 wsgi:app
```

Test gunicorn in debug mode binding to socket.
```
gunicorn --workers 3 --log-level deketbug --error-logfile error.log \
    --bind unix:twitter2kinesis.sock -m 007 wsgi:app
```

Run nginx tests.
```
sudo nginx -t
```

Check ports in use.
```
netstat -plnt
```

Check all active connections.
```
netstat -a
```

If need be, kill any processes using a specific port.
```
sudo fuser -k 80/tcp
```

Check facts.
```
ansible webservers -m setup
```
