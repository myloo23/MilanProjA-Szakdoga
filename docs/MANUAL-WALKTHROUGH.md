# Manual Docker Walkthrough

This document records the commands I used to manually build, run, and verify the Flask application inside a Docker container.

---

## 1. Build the Docker image

```bash
docker build -t flaskapp:manual .
```

Built a Docker image from the Dockerfile and tagged it as `flaskapp:manual`.

---

## 2. Run the Docker container

```bash
docker run --name flaskapp-manual -p 8000:8000 flaskapp:manual
```

Started a Docker container from the image and mapped port 8000 on the host to port 8000 inside the container.

---

## 3. Test the application

```bash
curl http://localhost:8000
```

Verified that the Flask application was running and responding to HTTP requests.

---

## 4. Stop the container

```bash
docker stop flaskapp-manual
```

Stopped the running Docker container.

---

## 5. Remove the container

```bash
docker rm flaskapp-manual
```

Removed the stopped container while keeping the Docker image.

---

## Issue encountered

Initially, the container failed with the following error:

```text
Error: Failed to find Flask application or factory in module 'app'
```

The Flask application was located in:

```text
app/app.py
```

while the Docker working directory was:

```text
/app
```

Because of this, Flask could not locate the application.

To fix the issue, the Dockerfile was updated by changing the working directory before running Flask:

```dockerfile
WORKDIR /app/app/
```

After rebuilding the Docker image, the application started successfully.