## Part 0: Setup and Prerequisites

In this step, we will verify that your system provides all necessary tools to run 

### Verify Python Installation

Check Python version:

```bash
python --version
```

To use SeBS, you need Python 3.7 or newer.

### Verify Docker Installation

```bash
docker --version

docker run hello-world
```

**If you see a permission denied error:**
```bash
sudo usermod -aG docker $USER
```

Then, try to run the `hello-world` command again in a new shell.

### Install Required Tools

In the tutorial, we use `jq` to parse JSON outputs. Additionally, we recommend installing cURL dependencies to avoid issues when installing `pycurl` library.

First, check that `jq` is functional:

```bash
sudo apt-get update && sudo apt-get install -y jq

echo '{"name": "test"}' | jq '.name'
```

Expected output: `"test"`

On Ubuntu, these packages should be sufficient to install `

sudo apt-get install libssl-dev libcurl4-openssl-dev 

### Clone and Install SeBS

In this step, we will clone the SeBS repository and install it with support for all cloud and local platforms. SeBS will create a Python virtual environment to manage dependencies. After these steps, we will be ready to deploy benchmarks.

```bash
git clone --recursive https://github.com/spcl/serverless-benchmarks.git
cd serverless-benchmarks
```

Install SeBS with local and OpenWhisk support

```bash
./install.py --aws --azure --gcp --local --openwhisk
```

Activate Python virtual environment

```bash
source python-venv/bin/activate
```

Verify SeBS installation

```bash
./sebs.py --help
```

**Expected output:**

```bash
Usage: sebs.py [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  benchmark
  experiment
  local
  resources
  storage
```


### Understand SeBS Architecture

SeBS has four main commands:

1. **`benchmark`**: Deploy and invoke individual functions.
2. **`experiment`**: Run systematic experiments (perf-cost, invocation overhead, container eviction, etc.)
3. **`storage`**: Manage object storage (MinIO and ScyllaDB for local deployment or OpenWhisk)
4. **`local`**: Manage local Docker deployments
5. **`resources`**: Manage resources created in the cloud.

Here are few essential concepts that will make 

* **SeBS Workflow:**
```
benchmark code → build code package / container → deploy to platform → invoke → measure
```
* **Caching:** SeBS manages a cache in the `cache` directory to remember all resources created in the cloud, as well as cache all built code packages and containers.
* **Resource ID:** each SeBS deployment uses a randomly generated resource ID to uniquely identify resources (functions, storage buckets, etc.) created in the cloud. When setting up a new cache directory in SeBS, you can provide a custom resource ID to reuse existing resources.
