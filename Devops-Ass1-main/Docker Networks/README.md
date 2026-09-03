# Docker Networking & Volumes - Homework

Practice of Docker container networking, host network, bind mounts, and overlay networks.

## Task 1: Docker Container Networking

Created 3 containers (frontend, backend, database) across 3 networks, with the **backend
connected to multiple networks** so it can bridge the frontend and the database.

| Container | Image | Network(s) |
|---|---|---|
| frontend | vansh-nginx-app | frontend-net |
| backend | vansh-nginx-app | backend-net + frontend-net + db-net |
| database | vansh-nginx-app | db-net |

> Note: all three tiers run `vansh-nginx-app` - the image I built myself in the
> `Docker Fundamentals` folder. What this task actually tests is the networking
> (multiple networks, DNS by container name, isolation between networks), and that is
> identical whatever server sits in each tier. Using my own image also makes the
> connectivity output easy to recognise: a successful request returns my own page.

### Create 3 networks
```bash
docker network create frontend-net
docker network create backend-net
docker network create db-net
docker network ls
```

### Create the 3 containers
```bash
docker run -d --name frontend --network frontend-net vansh-nginx-app
docker run -d --name backend  --network backend-net  vansh-nginx-app
docker run -d --name database --network db-net       vansh-nginx-app
```

### Add the backend to 2 more networks
```bash
docker network connect frontend-net backend
docker network connect db-net backend

# backend is on networks: backend-net db-net frontend-net
```

### Check connectivity
```bash
# backend -> frontend (shared frontend-net): SUCCESS
docker exec backend wget -qO- http://frontend        # returns my Nginx page

# backend -> database (shared db-net): SUCCESS
docker exec backend wget -qO- http://database        # returns my Nginx page

# frontend -> database (no shared network): FAILS, the name will not even resolve
docker exec frontend wget -qO- --timeout=5 http://database
# wget: bad address 'database'      (exit status 1)
```

**What I understood:** Containers on the **same** Docker network can reach each other by
name (Docker provides built-in DNS). Containers on **different** networks are isolated. By
attaching the backend to multiple networks, it can talk to both the frontend and the
database, while the frontend still cannot reach the database directly - which is how a real
3-tier app keeps the database private.

![Task 1 - networking](screenshots/image1.png)

## Task 2: Host Network

```bash
docker run -d --name web-host --network host vansh-apache-app
docker ps --filter name=web-host   # note: the PORTS column is EMPTY

# fetch it from inside the container, straight off the host's own port 80.
# httpd:2.4 ships no curl/wget, so I used bash's built-in /dev/tcp:
docker exec web-host bash -c 'exec 3<>/dev/tcp/localhost/80; \
  printf "GET / HTTP/1.0\r\n\r\n" >&3; cat <&3'
# HTTP/1.1 200 OK ... <h1>Hello World from Vansh's Apache HTTP Server!</h1>
```

**What I understood:** With `--network host`, the container shares the host's network
directly - no port mapping (`-p`) is needed, and the service is available on the host's own
port 80.

> Note: I ran my own `vansh-apache-app` image (built on `httpd:2.4`) for this task. On a
> native Linux host, `--network host` makes the server reachable directly at
> `http://localhost:80` from the host. I am on Docker Desktop for Mac, where the container
> joins the *Docker VM's* network namespace rather than macOS's, so I verified it from
> inside that namespace - which is exactly where the host network lives. The
> point of the task still holds: no `-p` flag was used and the `PORTS` column is empty.

![Task 2 - host network](screenshots/image2.png)

## Task 3: Bind Mount

```bash
# Create a local folder and file
mkdir site
echo "<h1>Hello from Vansh's bind mount</h1>" > site/index.html

# Bind mount the folder into Nginx (:ro = read-only inside the container)
docker run -d --name nginx-bind -p 8090:80 \
  -v "$(pwd)/site":/usr/share/nginx/html:ro vansh-nginx-app

# Access it
curl http://localhost:8090      # <h1>Hello from Vansh's bind mount</h1>

# Modify the file WITHOUT restarting the container
echo "<h1>Hello from Vansh's bind mount - edited live, no rebuild!</h1>" > site/index.html
curl http://localhost:8090      # <h1>Hello from Vansh's bind mount - edited live, no rebuild!</h1>
```

**What I understood:** A bind mount links a folder on my machine directly into the
container. Any edit I make to the local file appears immediately inside the container - no
rebuild or restart needed. This is very useful during development.

![Task 3 - bind mount](screenshots/image3.png)

## Task 4: Overlay Network (Research)

**What it is:** An overlay network connects containers running on **different Docker hosts**
(different physical/virtual machines) so they behave as if they are on one single network.

**How it works:** Docker creates a virtual network that spans multiple hosts. It encapsulates
container traffic (using VXLAN) and sends it over the physical network between the hosts, so
a container on Host A can talk to a container on Host B by name, without exposing ports on
each host. It requires a key-value store / cluster manager - in practice **Docker Swarm** (or
Kubernetes) provides this.

**Use cases:**
- Multi-host container communication in a cluster.
- Docker Swarm services that scale containers across many nodes.
- Microservices that run on different servers but need to talk to each other securely.

**Bridge vs Overlay:**
| | Bridge network | Overlay network |
|---|---|---|
| Scope | Single host | Multiple hosts |
| Use case | Containers on one machine | Containers across a cluster |
| Needs orchestrator | No | Yes (Swarm/Kubernetes) |

**Example (on a Swarm):**
```bash
docker swarm init
docker network create -d overlay my-overlay
docker service create --name web --network my-overlay nginx
```

## Cleanup commands used
```bash
docker rm -f frontend backend database web-host nginx-bind
docker network rm frontend-net backend-net db-net
```
