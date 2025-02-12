# #!/bin/bash

# # Ensure /data directory exists
# mkdir -p /data

# # Copy cookies.txt to /data
# cp ./cookies.txt /data/cookies.txt

# # Start the Gunicorn server
# gunicorn app:app
#!/bin/bash

# Ensure the /data directory exists (should already exist from Render)
mkdir -p /data

# Check if cookies.txt exists before copying (to avoid overwriting)
if [ ! -f /data/cookies.txt ] && [ -f ./cookies.txt ]; then
    cp ./cookies.txt /data/cookies.txt
fi

# Start the Gunicorn server
gunicorn --bind 0.0.0.0:8080 --workers 4 --threads 2 --timeout 120 app:app

