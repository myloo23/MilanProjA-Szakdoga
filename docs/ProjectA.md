# TCS DevOps Internship Program: Project Assignments

## General Instructions

- There are 4 projects (A-D); each participant selects one.
- Officially, the project work is completed and submitted individually; the deliverable is your own.
- Helping each other is encouraged, not restricted. If someone asks, share generic
  solutions and knowledge (e.g. how to install tooling without admin rights on a TCS laptop).
- Try to solve problems yourself first. **Never ask for, or hand over, a whole solution.**
- You must be able to **explain how your configuration or code works**.
- The end-to-end solution must run **on a local machine**.
- Deliverables:
  - Setup & configuration
  - A working demo
  - Clear documentation (PDF / Word / Markdown preferred)
  - A weekly progress demo with mentors, plus a final live demo session at the end of the project

---

## Projects

## Project A: Classic CI/CD

### Why choose this project

- **CI/CD is the backbone of DevOps.** Kubernetes is one deployment target. Pipelines
  are what actually get code from a commit into any environment (VMs, containers,
  serverless, or clusters). Learn the backbone first.
- **Most real workloads are not on Kubernetes.** A huge share of production systems still
  run on plain VMs and Docker hosts. Knowing how to ship to them is a daily-use skill.
- **It runs on a modest laptop.** No 8 GB cluster eating your RAM. You iterate faster and
  spend time learning instead of fighting minikube.
- **It is what interviews test.** "Walk me through your pipeline" comes up far more often
  than "explain a Helm chart". You will build the exact story interviewers want.
- **You still get the fun toys.** Modern self-hosted CI (Gitea Actions, Woodpecker) plus
  Docker, Prometheus, Grafana and Loki give you a full, satisfying, end-to-end stack.
- **It composes with everything else.** Once your pipeline works, bolting Kubernetes,
  Terraform, or tracing on top later is easy. The reverse is not true.

### Objective

Implement a classic Continuous Integration / Continuous Deployment pipeline for a sample
application. Automate the path from code commit through build and test to deployment on a
local environment, with monitoring and logging for observability. Requirements are
intentionally open-ended so you can pick your own tools and design the stages.

### User story examples

- *As a developer,* I want code merged to `main` to deploy automatically to a dev
  environment, so new changes are integrated and tested quickly.
- *As a DevOps engineer,* I want the deployment automated and consistent, to minimize
  manual errors and speed up delivery.
- *As a team,* we want to monitor the app and collect logs, to detect issues and
  performance problems early.

### Key features & guidelines

Build a pipeline that runs on each commit and includes:

1. **Build & test stages** (compile / run unit tests for the sample app).
2. **Build stage produces a Docker image as the pipeline artifact** (see "Build artifact &
   local deployment" below).
3. **Deploy stage driven by Ansible.** Use an Ansible playbook to run the image as a
   container on a local Docker host. Ansible is the recommended automation tool here; a
   plain shell script is an acceptable fallback.
4. The sample app is a small web service (the Flask starter below), containerized with Docker.
5. **Monitoring:** Prometheus + Grafana dashboards for metrics (CPU, memory, custom app metrics).
6. **Logging:** aggregate and search application logs (see the logging scenario below).

### CI/CD tool options (choose one)

The original suggested GitLab CI or Jenkins. Both still work and are free, but here is the
modern, lighter menu, great for a laptop:

| Tool | Notes | Weight |
|------|-------|--------|
| **[Gitea](https://about.gitea.com/) + [Gitea Actions](https://docs.gitea.com/usage/actions/overview)** | Self-hosted Git plus a GitHub-Actions-compatible runner. Very light, modern, fun. **Recommended.** | Light |
| **[Forgejo](https://forgejo.org/) Actions** | Community fork of Gitea, same Actions model. | Light |
| **[Woodpecker CI](https://woodpecker-ci.org/)** | Small, container-native pipelines (a community fork of Drone). | Light |
| **Jenkins** | The classic. Heavier, but ubiquitous in the enterprise, good to know. | Medium |
| **GitLab CE (self-managed)** | Full-featured but resource-hungry locally. GitLab.com's free tier CI minutes are now limited. | Heavy |
| **GitHub Actions + self-hosted runner** | If your repo is already on GitHub. | Light |
| **[Drone CI](https://www.drone.io/)** | Now owned by Harness; still open source. | Medium |

> **Tip:** A Gitea + Gitea Actions + Docker + Prometheus/Grafana/Loki stack gives you the
> full modern experience with a fraction of GitLab's footprint.

### Build artifact & local deployment

The artifact your pipeline produces is a **Docker image**. The interesting question is how
that image gets from the build stage to a running container on your local machine, without
introducing Kubernetes. Keep it small: the "target environment" is just a **Docker host**
(your laptop, or a lightweight local VM). Two approaches, from simplest to more realistic:

1. **Build and run on the same host (simplest).** The build stage builds the image locally;
   the deploy stage runs it directly with Ansible. No registry needed. This is enough to
   demonstrate the full commit-to-running-container flow.
2. **Push to a local registry, then pull (more production-like).** Run a local registry as a
   container (`docker run -d -p 5000:5000 --name registry registry:2`). The build stage
   tags and pushes the image to `localhost:5000/myapp:<tag>`; the deploy stage pulls that
   exact tag and runs it. This mirrors real pipelines: build once, deploy an immutable,
   versioned artifact.

Do **not** use k3s or Kubernetes for this project. The point is to master the classic
build-artifact-deploy loop on a plain Docker host; the Kubernetes path is Project C.

**Automating the deploy with Ansible.** Ansible has an officially maintained
**[`community.docker`](https://galaxy.ansible.com/ui/repo/published/community/docker/)**
collection, so you do not have to script raw `docker` commands. Install it once with:

```bash
ansible-galaxy collection install community.docker
```

Then your playbook can build or pull the image and run the container declaratively:

```yaml
- name: Deploy the app container
  hosts: local_docker
  tasks:
    - name: Pull the image from the local registry
      community.docker.docker_image:
        name: localhost:5000/myapp
        tag: "{{ app_version }}"
        source: pull

    - name: Run the container
      community.docker.docker_container:
        name: myapp
        image: "localhost:5000/myapp:{{ app_version }}"
        state: started
        recreate: true
        published_ports:
          - "5000:5000"
        restart_policy: unless-stopped
```

Because `community.docker.docker_container` is idempotent, re-running the playbook with a
new image tag cleanly replaces the running container, which is exactly the "update the
deployment automatically" behaviour the user stories ask for. This keeps Ansible at the
centre of the deploy stage without pulling in any orchestration platform.

### Logging: a real-world scenario

Metrics tell you *that* something is wrong; logs tell you *why*. Wire logging the way you
would in production so it becomes a genuine part of the pipeline rather than an afterthought.

The scenario: your pipeline has just deployed the Flask container. A user reports that some
requests are failing intermittently. You do not SSH into the box and `grep` through files,
you open Grafana, spot the spike, and pivot straight to the matching logs.

Set it up like this:

- The Flask app logs to **stdout** as structured lines (ideally JSON), never to a file
  inside the container. This is the twelve-factor approach: the platform owns the logs,
  not the app.
- A log shipper (Grafana Alloy or Promtail) tails the container's stdout and pushes entries
  into **Loki**.
- In Grafana you query those logs with LogQL, right next to your metric dashboards.

Then prove it works with an incident-style walkthrough:

1. Send a burst of good and bad requests to `/echo` (some with invalid JSON).
2. Watch the request-rate / error metric spike on your Grafana dashboard.
3. Pivot to Loki, filter for `level=ERROR` and the `/echo` path, and find the exact failing
   requests and their payloads.

That metric-to-log pivot (notice a spike, jump to the matching logs) is exactly how on-call
engineers debug real systems.

Tooling: prefer **Grafana Loki** for local work; it is lightweight and lives inside the same
Grafana you already run for metrics. The ELK / OpenSearch stack remains a valid option if
you specifically want to learn full-text log search, but it is heavier on a laptop.

### Expectations

- Working CI pipeline (build + test)
- Automatically deployed Docker container
- Dashboards in Grafana
- Basic log searching (Loki, or ELK / OpenSearch)

### Starter code: `app.py`

```python
# app.py
from flask import Flask, jsonify, request
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    app.logger.info("Home route called")
    return "Hello from Flask!"

@app.route('/health')
def health():
    return jsonify(status="UP")

@app.route('/echo', methods=['POST'])
def echo():
    data = request.json
    app.logger.info(f"Echo received: {data}")
    return jsonify(received=data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### Useful links

- Gitea Actions: https://docs.gitea.com/usage/actions/overview
- Woodpecker CI: https://woodpecker-ci.org/docs/intro
- GitLab CI/CD: https://docs.gitlab.com/ee/ci/
- Jenkins: https://www.jenkins.io/doc/
- Ansible: https://docs.ansible.com/
- Ansible `community.docker` collection: https://docs.ansible.com/ansible/latest/collections/community/docker/
- Prometheus: https://prometheus.io/docs/
- Grafana Loki (recommended logging): https://grafana.com/oss/loki/
- ELK reference: https://www.elastic.co/what-is/elk-stack

---