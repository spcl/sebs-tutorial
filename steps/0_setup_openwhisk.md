# OpenWhisk Deployment

Open-source FaaS platforms - like OpenWhisk, Fission, Knative - are typically deployed on Kubernetes clusters.
You can deploy them anywhere, e.g., on a managed Kubernetes instance in the cloud.
Here, we use a minimalistic Kubernetes installation `kind`.
If you deploy OpenWhisk on an existing Kubernetes cluster, then please configure the `wsk` CLI tool to point to it - SeBS does not need anything else to use an OpenWhisk installation.

## Requirements & Prerequisites

### DockerHub Account

SeBS uses Docker containers to deploy functions on OpenWhisk due to small size limit on code packages.
To that end, you need a DockerHub account to push containers, as private Docker registries do not work well on `kind` and `OpenWhisk`.
If you don't have an account, then create [a free one](https://www.docker.com/products/personal/), and create a test repository for your functions.
In the command line, use `docker login` to activate your account.
Make sure that your registry is public - otherwise, OpenWhisk won't able to pull function images.

Then, change SeBS configuration by updating the default docker repository

```json
{
  "general": {
    "docker_repository": "spcleth/serverless-benchmarks",
    "SeBS_version": "1.2.0"
  },
```

### Install OpenWhisk Prerequisites

We will install the following tools to deploy OpenWhisk:
- `kind 0.22` (minimal Kubernetes cluster based on Docker)
- `kubectl 1.20.0` (management tool for Kubernetes clusters)
- `helm 3.14.4` (package manager for Kubernetes, used by OpenWhisk deployment)
- `wsk 1.20` (OpenWhisk CLI tool)
While newer versions of these tools can be used, this configuration has been verified to work with OpenWhisk.

### Check Go Installation

OpenWhisk preparation script requires Go:

```bash
go version
```

If Go is not found, then install a relatively recent version with your OS package manager or the Go's binary distribution.

### Install Dependencies

We assume that all tools are installed in `openwhisk-deps` in the current directory:

```bash
DEPS_PATH=$(pwd)/openwhisk-deps

GOBIN=${DEPS_PATH} go install sigs.k8s.io/kind@v0.22.0

curl -LO https://dl.k8s.io/release/v1.20.0/bin/linux/amd64/kubectl
chmod +x kubectl
mv kubectl ${DEPS_PATH}

wget https://get.helm.sh/helm-v3.14.4-linux-amd64.tar.gz
tar -xf helm-v3.14.4-linux-amd64.tar.gz
mv linux-amd64/helm ${DEPS_PATH}

wget https://github.com/apache/openwhisk-cli/releases/download/1.2.0/OpenWhisk_CLI-1.2.0-linux-amd64.tgz
tar -xf OpenWhisk_CLI-1.2.0-linux-amd64.tgz
mv wsk ${DEPS_PATH}

export PATH=${DEPS_PATH}/bin:${PATH}
```

## Deploy OpenWhisk 

Clone the OpenWhisk deployment repository:

```bash
git clone git@github.com:apache/openwhisk-deploy-kube.git
```

Before we deploy OpenWhisk, we need to adjust its configuration to support all benchmarks.
Default configuration allows functions to use not more than 512 MB of memory, which is insufficient for some benchmarks.
In `helm/openwhisk/values.yaml`, find the following settings:

```yaml
  limits:
    actionsInvokesPerminute: 60
    actionsInvokesConcurrent: 30
    triggersFiresPerminute: 60
    actionsSequenceMaxlength: 50
    actions:
      time:
        min: "100ms"
        max: "5m"
        std: "1m"
      memory:
        min: "128m"
        max: "512m"
        std: "256m"
```

We want to change the `limits.actions.memory.max` value to something larger, e.g., "3072m".

Then, in the repository, run the following command to start a Kubernetes cluster:

```bash
./deploy/kind/start-kind.sh
```

The process can take a few minutes, with most of the time needed to obtain Docker images:

```
Creating cluster "kind" ...
⢄⡱ Ensuring node image (kindest/node:v1.20.7) 🖼
 ✓ Ensuring node image (kindest/node:v1.20.7) 🖼
 ✓ Preparing nodes 📦 📦 📦
 ✓ Writing configuration 📜
 ✓ Starting control-plane 🕹️
 ✓ Installing CNI 🔌
 ✓ Installing StorageClass 💾
 ✓ Joining worker nodes 🚜
 ✓ Waiting ≤ 10m0s for control-plane = Ready ⏳
 • Ready after 0s 💚
Set kubectl context to "kind-kind"
You can now use your cluster with:

kubectl cluster-info --context kind-kind
```

You can verify that a cluster has been created:

```bash
kind get clusters
kind
```

Now, we can start the OpenWhisk deployment:

```bash
helm install owdev ./helm/openwhisk -n openwhisk --create-namespace -f deploy/kind/mycluster.yaml
```

The command will return immediately, but the entire process will run in the background for few minutes.
You can use this command to wait until all pods are in the `Running` or `Completed` state:

```bash
kubectl get pods -n openwhisk --watch
```

Once you see the invoker tests and prewarming containers, your OpenWhisk deployment should be finished:

```
wskowdev-invoker-00-6-whisksystem-invokerhealthtestaction0   1/1     Running       0          10s
wskowdev-invoker-00-7-prewarm-nodejs14                       1/1     Running       0          8s
```

Finally, we need to configure the `wsk` to correctly connect to the OpenWhisk deployment:

```bash
wsk property set --apihost localhost:31001
wsk property set --auth '23bc46b1-71f6-4ed5-8c54-816aa4f8c502:123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP'
```

### Verify OpenWhisk Installation

Check that the wsk CLI is functional. The following command should return an empty list of *actions* - this is the OpenWhisk lingo for functions.

```bash
wsk action list
```

You can also verify cluster nodes:

```bash
kubectl get nodes -n openwhisk
```

You should see three nodes:

```
NAME                 STATUS   ROLES                  AGE     VERSION
kind-control-plane   Ready    control-plane,master   10m     v1.20.7
kind-worker          Ready    <none>                 9m27s   v1.20.7
kind-worker2         Ready    <none>                 9m27s   v1.20.7
```

## Configure Storage for OpenWhisk

OpenWhisk pods need to access MinIO from inside Kubernetes,
which requires a slightly different procedure than for the local deployment.
We must expose MinIO with an externally accessible IP.

First, deploy the storage as in the previous exercise:

```bash
./sebs.py storage start object config/storage.json \
    --output-json outputs/storage_ow.json
```

### Get External IP Address

Get the primary IP address of your machine. This will be used by OpenWhisk functions to access the MinIO storage instance.

```bash
export EXTERNAL_IP=$(hostname -I | awk '{print $1}')
echo "External IP: $EXTERNAL_IP"
```

**Important:** This should NOT be `127.0.0.1` (won't work from Kubernetes pods).

The actual address will be `${EXTERNAL_IP}:${MAPPED_PORT}`, where `MAPPED_PORT` is by default the port `9011`.
You can verify the exact port by checking the output of the storage start command.

**Test connectivity from host:**
```bash
curl -s http://$EXTERNAL_IP:9011/minio/health/live
```
Expected: Empty response (200 OK) means MinIO is accessible

### Update Storage Configuration

```bash
# Update MinIO address to use external IP
jq --arg ip "$EXTERNAL_IP" \
   '.object.minio.address = ($ip + ":9011")' \
   outputs/storage_ow.json > outputs/storage_ow_ext.json

# Verify the updated address
jq '.object.minio.address' outputs/storage_ow_ext.json
```

Expected: `"<your-external-ip>:9011"` (not 127.0.0.1:9011)

## Configure DockerHub Repository for OpenWhisk

Update the SeBS configuration file to use your DockerHub repository. Edit the `deployment.openwhisk.dockerhubRepository` field in your configuration file to point to your DockerHub username and repository (e.g., `username/repository-name`).

This configuration will be used when deploying functions to OpenWhisk in the next tutorial steps.
