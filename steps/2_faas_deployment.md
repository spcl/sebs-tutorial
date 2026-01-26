# Part 2: FaaS Platforms, Modifying Functions, and Experiments

In this session, you will learn to deploy functions to an actual FaaS platform, how to modify functions to deploy new versions and workloads,
and how to conduct automatic experiments.

For this part, you can use any of three supported FaaS platforms - AWS, Azure, GCP.
Please check [SeBS documentation](https://github.com/spcl/serverless-benchmarks/blob/master/docs/platforms.md) to find instructions how to set up credentials for your platforms.
Otherwise, you can deploy OpenWhisk on your system - for that part, please follow [the instructions on deploying this FaaS system](0_setup_openwhisk.md).

## Deploy Benchmarks

We will start with the `210.thumbnailer` benchmark, as in the previous experiment.

### Configuration

For deployment with OpenWhisk, you need [a free DockerHub account](https://www.docker.com/products/personal/) as function containers need to be pushed to a publicly available repositories.
You can provide it in `deployment.openwhisk.dockerhubRepository` in the configuration file.

In addition, we supply the storage configuration to connect to the MinIO instance started in the deployment steps:

```bash
jq --arg ip ${EXTERNAL_IP} --slurpfile file1 outputs/storage.json '.deployment.openwhisk.storage = $file1[0] | .deployment.openwhisk.storage.object.minio.address = ($ip + ":9011")' <tutorial-dir>/configs/openwhisk.json > outputs/openwhisk_deployment.json
```

When deploying to cloud platforms like AWS, Azure, or GCP, we do not need to manually set up object storage, as these platforms provide their own storage services.
You can run all following exercises on these platforms.
Only steps specific to OpenWhisk - like querying list of executions with `wsk` - will be skipped.
Instead, you can obtain the same information from the cloud's web interface.

### Deploy & Invoke

Deploy and invoke benchmark with the following command. The provided JSON config file will determine most of the configuration, such as cloud platform and language runtime. In this example, we use OpenWhisk:

```bash
./sebs.py benchmark invoke 210.thumbnailer test \
    --config outputs/openwhisk_deployment.json  \
    --container-deployment \
    --output-dir results \
    --repetitions 5
```

**Command breakdown:**
- `benchmark invoke`: Invoke the function.
- `210.thumbnailer`: Benchmark to deploy
- `test`: Input size
- `outputs/openwhisk_deployment.json`: Configuration file
- `--container-deployment`: Enforce deployment of functions as Docker containers.
- `--output-dir results`: Results of benchmark execution will be stored in `results` directory.
- `--repetitions 5`: Number of repetitions of the benchmark.

**Note**: Container deployment is required for OpenWhisk, as it does not support uploads of larger code packages. However, it is not necessary for cloud platforms, which can deploy functions directly from code packages, and it is not supported on Azure and GCP.

**Expected behavior:**

This operation will first initialize the deployment, as in the previous step:

```
OpenWhisk.Resources-994c Using user-provided configuration of storage type: object for openwhisk containers.
OpenWhisk.Resources-994c Deserializing access data to Minio storage
OpenWhisk.Resources-994c No NoSQL storage available
OpenWhisk.Resources-994c Using cached Docker registry for OpenWhisk
OpenWhisk-121a Using existing resource name: 978b3035.
minio.Minio-15ed Upload benchmarks-data/200.multimedia/210.thumbnailer/6_astronomy-desktop-wallpaper-evening-1624438.jpg to sebs-benchmarks-978
...
```

Then, SeBS will build a container with the function benchmark and push it to the Docker registry; in this case, we push to the repository `spcleth/test-openwhisk` to the DockerHub.

```
Benchmark-98b9 Building benchmark 210.thumbnailer. Reason: no cached code package.
Benchmark-98b9 There is no Docker build image for openwhisk run in python, thus skipping the Docker-based installation of dependencies.
OpenWhisk.Container-35d5 Build the benchmark base image spcleth/test-openwhisk:function.openwhisk.210.thumbnailer.python-3.9-x64-1.2.0.
OpenWhisk.Container-35d5 Push the benchmark base image spcleth/test-openwhisk:function.openwhisk.210.thumbnailer.python-3.9-x64-1.2.0 to registry: Docker Hub.
OpenWhisk.Container-35d5 Pushing image function.openwhisk.210.thumbnailer.python-3.9-x64-1.2.0 to spcleth/test-openwhisk:function.openwhisk.210.thumbnailer.python-3.9-x64-1.2.0
```

This step created a new Docker image with a tag `function.openwhisk.210.thumbnailer.python-3.9-x64-1.2.0`, which encodes the platform, benchmark, runtime language, language version, CPU architecture, and SeBS version.

We use the same benchmark implementation as for the local deployment.
To understand how this works, we can inspect the main entrypoint of the function `210.thumbnailer_code/python/3.9/x64/container/__main__.py`.
There, we create a connection between the OpenWhisk interface and our benchmark implementation.
In addition, we set up the storage configuration to allow functions to connect to the MinIO instance.

```python
def main(args):
    begin = datetime.datetime.now()
    args['request-id'] = os.getenv('__OW_ACTIVATION_ID')
    args['income-timestamp'] = begin.timestamp()

    for arg in ["MINIO_STORAGE_CONNECTION_URL", "MINIO_STORAGE_ACCESS_KEY", "MINIO_STORAGE_SECRET_KEY"]:
        os.environ[arg] = args[arg]
        del args[arg]

    try:
        from function import function
        ret = function.handler(args)
        end = datetime.datetime.now()
        logging.info("Function result: {}".format(ret))
        ...
```

These wrappers are defined in SeBS for each platform, and they are automatically included in the function's deployment during the build process.

Finally, we can create an *action*, the OpenWhisk name for function.

```
OpenWhisk-121a Created /work/2020/serverless/sebs/main/210.thumbnailer_code/python/3.9/x64/container/210.thumbnailer.zip archive
OpenWhisk-121a Zip archive size 0.000769 MB
Benchmark-98b9 Created code package (source hash: 09b5236e281b27bf14b97d5d66214d23), for run on openwhisk with python:3.9
OpenWhisk-121a Creating new function! Reason: function sebs-978b3035-210.thumbnailer-python-3.9 not found in cache.
OpenWhisk-121a Creating function as an action in OpenWhisk.
OpenWhisk-35e4 Creating new OpenWhisk action sebs-978b3035-210.thumbnailer-python-3.9
```

The newly created function will be invoked five times.

```
SeBS-fd9a Beginning repetition 1/5
SeBS-fd9a Beginning repetition 2/5
SeBS-fd9a Beginning repetition 3/5
SeBS-fd9a Beginning repetition 4/5
SeBS-fd9a Beginning repetition 5/5
SeBS-fd9a Save results to experiments.json
```

We can check how many different pods were created by OpenWhisk to handle our workloads:

```bash
kubectl get nodes -n openwhisk | grep wskowdev-invoker
```

### Check Function in the FaaS System 

In OpenWhisk, we can list all deployed actions:

```bash
wsk -i action list
```

You should something similar to this:

```
actions
/guest/sebs-978b3035-210.thumbnailer-python-3.9 private blackbox
```

You can inspect the action details:
```bash
wsk -i action get /guest/sebs-978b3035-210.thumbnailer-python-3.9
```

Which will return the Docker image, memory configuration, timeout,
and the list of environment variables that contain access details to the object storage.

```
{
    "namespace": "guest",
    "name": "sebs-978b3035-210.thumbnailer-python-3.9",
    "version": "0.0.1",
    "exec": {
        "kind": "blackbox",
        "image": "spcleth/serverless-benchmarks:function.openwhisk.210.thumbnailer.python-3.9-x64-1.2.0",
        "binary": true
    },
    "parameters": [
        {
            "key": "MINIO_STORAGE_SECRET_KEY",
            "value": "XXXX"
        },
        {
            "key": "MINIO_STORAGE_ACCESS_KEY",
            "value": "XXXX"
        },
        {
            "key": "MINIO_STORAGE_CONNECTION_URL",
            "value": "XXXX:9011"
        }
    ],
    "limits": {
        "timeout": 60000,
        "memory": 256,
        "logs": 10,
        "concurrency": 1
    }
}
```

We can list all activations (invocations); this command might have to be repeated when the first invocation provides no results.

```bash
wsk -i activation list
```

You can select one of the activations and inspect the results, including the full response of the benchmark, as 
well as execution logs.

```bash
wsk -i activation get <activation-id>
```

### Examine Results

We can use the second benchmark command in SeBS - `statistics` - to summarize the execution:

```bash
./sebs.py benchmark statistics results/experiments.json
```

Results will be sorted into warm and cold executions, and all statistics will be split into three categories:
- Cloud provider metrics, such as execution and initialization time for cold starts. 
- Function metrics, such as total execution time, and intra-benchmark statistics (when available).
- Total execution time from client's perspective.

```
Statistics Processing cold results.
Statistics    Cloud provider measurements
Statistics    Intra-function measurements
Statistics            Measurement type function_exec, mean 215817.0, median 215817.0, std 6370.0, cv 2.9515747137621227.
Statistics            Measurement type compute, mean 28714.5, median 28714.5, std 671.5, cv 2.3385397621410786.
Statistics            Measurement type upload, mean 9388.0, median 9388.0, std 287.0, cv 3.0570941627609716.
Statistics            Measurement type download, mean 10178.0, median 10178.0, std 700.0, cv 6.87757909215956.
Statistics    Client measurements
Statistics            Measurement type client_exec, mean 20533001.0, median 20533001.0, std 435708.0, cv 2.1219888899825214.
Statistics Processing warm results.
Statistics    Cloud provider measurements
Statistics    Intra-function measurements
Statistics            Measurement type function_exec, mean 41663.666666666664, median 40177.0, std 2524.4609105488025, cv 6.059142443573064.
Statistics            Measurement type compute, mean 24830.0, median 24362.0, std 758.5793740055595, cv 3.0550921224549317.
Statistics            Measurement type upload, mean 9252.0, median 9138.0, std 349.09693018797327, cv 3.773205038780515.
Statistics            Measurement type download, mean 7075.666666666667, median 6457.0, std 1429.6737001459069, cv 20.205498188334293.
Statistics    Client measurements
Statistics            Measurement type client_exec, mean 64637.666666666664, median 59345.0, std 7538.056174431767, cv 11.662017772555375.
```

As you can notice, cloud provider metrics are missing - the `experiments.json` file does not contain them.
We need to run a third benchmark command - `process` - to download execution metrics from the cloud.
These two steps are distinct as some cloud platforms take several minutes to populate metrics.

```bash
./sebs.py benchmark process --config outputs/openwhisk_deployment.json --output-dir results --container-deployment
```

This should succeed by finding all invocations in OpenWhisk, which will be saved in the `results.json` file.

```
OpenWhisk-9276 OpenWhisk: Starting to download metrics for 5 invocations
OpenWhisk-9276 OpenWhisk: Downloaded metrics for 5 out of 5 invocations
SeBS-e85b Save results to results/results.json
```

After rerunning statistics on the new results file, we should see cloud provider metrics:

```bash
Statistics Processing cold results.
Statistics    Cloud provider measurements
Statistics            Measurement type init, mean 214000.0, median 214000.0, std 4000.0, cv 1.8691588785046727.
Statistics            Measurement type provider_exec, mean 432500.0, median 432500.0, std 10500.0, cv 2.4277456647398843.
...
Statistics Processing warm results.
Statistics    Cloud provider measurements
Statistics            Measurement type provider_exec, mean 44666.666666666664, median 43000.0, std 3091.2061651652343, cv 6.920610817534108.
```

### From Python to Node.js

We can easily switch SeBS experiments between available language versions.
Different language runtimes may have different performance characteristics, as they will use the best suiting libraries and implementations.
However, each version should implement the same logic and produce similar results.

For example, we can redeploy `210.thumbnailer` in Node.js instead of Python:

```bash
./sebs.py benchmark invoke 210.thumbnailer test \
    --config outputs/openwhisk_deployment.json  \
    --container-deployment \
    --output-dir results \
    --repetitions 5 \
    --language nodejs \
    --language-version 20
```

All other steps, such as analyzing timings and the results produced such be similar to the benchmark version for Python,
with the difference in fewer intra-function measurements provided by the Node.js implementation.

---

## Function Modification

In this part, we will adapt slightly an existing benchmark to demonstrate how easily new workloads can be executed in SeBS.

### Create "New" Function

First, we will create a "new" benchmark function `110.dynamic-html-new`.

```bash
cp -r benchmarks/100.webapps/110.dynamic-html benchmarks/100.webapps/110.dynamic-html-new
```

In [`examples/new_dynamic_html.py`](examples/new_dynamic_html.py), we have prepared a modified version of the original function that includes three major changes:
* Extensive logging of all steps, which can be helpful in debugging and resolving crashes.
* Additional time measurements, which are now returned as part of the result - similarly to the `210.thumbnailer` benchmark.
* Use of the [`faker`](https://pypi.org/project/Faker/) library to generate random information about the user.

You can view the changes introduced in the new version:

```bash
diff <tutorial-dir>/examples/new_dynamic_html.py benchmarks/100.webapps/110.dynamic-html-new/python/function.py
```

Then, for a successful deployment, we need to extend new benchmark to the SeBS configuration.

```bash
echo 'faker==30.0.0' >> benchmarks/100.webapps/110.dynamic-html-new/python/requirements.txt
```

No other changes are needed, as SeBS will automatically detect the new benchmark based on the directory structure.

When manually manually and redeploying benchmarks, SeBS will notice that the code has changed and redeploy the code package automatically.
You will notice this by the presence of the following line in the output:

```
Benchmark-1212 Building benchmark 110.dynamic-html-new. Reason: cached code package is not up to date/build enforced.
```
However, OpenWhisk actions might not immediately adapt the new Docker image as they will keep existing warm workers.

Additionally, you can force SeBS to rebuild the code package by passing the `--update-code` flag.

### Deploy New Function

The only change to the deployment code involves changing the benchmark name.

```bash
./sebs.py benchmark invoke 110.dynamic-html-new test \
    --config outputs/openwhisk_deployment.json  \
    --container-deployment \
    --output-dir results \
    --repetitions 5
```

**Expected behavior:**

We can check the changes - faked data and new measurements - in the results file:

```json
cat experiments.json | jq '._invocations[<function-name>] | to_entries[0].value.output.result'
```

This will show both the changed the result (HTML template) and the new measurements:

```
{
  "measurement": {
    "generation_time": 53.64418029785156,
    "rendering_time": 1926.8989562988281,
    "total_time": 27203.55987548828
  },
  "result": "<!DOCTYPE html>\n<html>\n  <head>\n    <title>Randomly generated data.</title>\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <link href=\"http://netdna.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap.min.css\" rel=\"stylesheet\" media=\"screen\">\n    <style type=\"text/css\">\n      .container {\n        max-width: 500px;\n        padding-top: 100px;\n      }\n    </style>\n  </head>\n  <body>\n    <div class=\"container\">\n      <p>Welcome testname, email: hodgescheryl@example.com, working as Health service manager!</p>\n      <p>Data generated at: 2026-01-26 00:35:58.548987!</p>\n      <p>Requested random numbers:</p>\n      <ul>\n        \n        <li>918518</li>\n        \n        <li>406496</li>\n        \n        <li>135206</li>\n        \n        <li>243970</li>\n        \n        <li>240459</li>\n        \n        <li>504032</li>\n        \n        <li>166307</li>\n        \n        <li>813461</li>\n        \n        <li>604639</li>\n        \n        <li>996574</li>\n        \n      </ul>\n    </div>\n  </body>\n</html>"
}
```

To access the additional outputs, we access OpenWhisk directly:

```bash
wsk -i activation get <activation-id> | tail -n +2 | jq '.logs'
```

Should produce result similar:

```
"2026-01-26T00:35:58.636417407Z stdout: INFO:root:[INFO] Handler invoked",
"2026-01-26T00:35:58.662753403Z stdout: INFO:root:[INFO] Username: testname, email: sarah86@example.com, working as Interpreter",
"2026-01-26T00:35:58.662790663Z stdout: INFO:root:[INFO] Random count: 10",
"2026-01-26T00:35:58.662801113Z stdout: INFO:root:[INFO] Generating 10 random numbers",
"2026-01-26T00:35:58.662804679Z stdout: INFO:root:[INFO] Rendering HTML template",
"2026-01-26T00:35:58.664563964Z stdout: INFO:root:[INFO] Generated HTML size: 1009 bytes",
"2026-01-26T00:35:58.664590915Z stdout: INFO:root:[INFO] Handler completed successfully",
"2026-01-26T00:35:58.664648383Z stdout: INFO:root:Function result: {'result': '<!DOCTYPE html>\\n<html>\\n  <head>\\n    <title>Randomly generated data.</title>\\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\\n    <link href=\"http://netdna.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap.min.css\" rel=\"stylesheet\" media=\"screen\">\\n    <style type=\"text/css\">\\n      .container {\\n        max-width: 500px;\\n        padding-top: 100px;\\n      }\\n    </style>\\n  </head>\\n  <body>\\n    <div class=\"container\">\\n      <p>Welcome testname, email: sarah86@example.com, working as Interpreter!</p>\\n      <p>Data generated at: 2026-01-26 00:35:58.662518!</p>\\n      <p>Requested random numbers:</p>\\n      <ul>\\n        \\n        <li>914916</li>\\n        \\n        <li>185787</li>\\n        \\n        <li>259290</li>\\n        \\n        <li>381223</li>\\n        \\n        <li>635695</li>\\n        \\n        <li>611395</li>\\n        \\n        <li>5429</li>\\n        \\n        <li>189919</li>\\n        \\n        <li>841930</li>\\n        \\n        <li>526378</li>\\n        \\n      </ul>\\n    </div>\\n  </body>\\n</html>', 'measurement': {'generation_time': 46.73004150390625, 'rendering_time': 1697.540283203125, 'total_time': 28314.828872680664}}"
```

---

## Running Experiments

SeBS supports several automatic experiment types to benchmark FaaS platforms:
- **perf-cost**: Measure performance in different scenarios.
- **container-eviction**: Study cold start frequency
- **network-ping-pong**: Network performance between function and the host.
- **invocation-overhead**: Estimate function invocation latency.

In this last exercise, we will run a simple `perf-cost` experiment on OpenWhisk.

### Perf-Cost Experiment

The experiment is defined by four main parameters: `repetitions`, `concurrent-invocations`, `memory-sizes`, and `experiments`.
Intuitively, we invoke functions in parallel with `concurrent-invocations` samples, repeating until we gather `repetitions` samples.
Then, we execute it for each memory size configuration of the benchmark function and for each invocation policy defined in `experiments`.
The `perf-cost` experiment implements four invocation policies:
* `cold` enforces killing containers between batches to gather as many cold starts as possible.
* `warm` gathers only warm samples, and reject cold invocations.
* `burst` invokes functions and gather both warm and cold samples.
* `sequential` invokes functions with no parallelism.

In OpenWhisk, we use `warm` invocations as we we do not currently have any reliable method of enforcing container eviction.
While we were successful with enforcing container eviction on cloud platforms by modifying specific function parameters,
OpenWhisk does not terminate warm containers even if action's parameters are changed.

### Experiment Configuration

You can examine the basic configuration of the `perf-cost` experiment:

```bash
cat configs/experiment_perf_cost.json | jq '.experiments."perf-cost"'
```

We use the following parameters:

```json
{
  "benchmark": "110.dynamic-html",
  "experiments": [
    "warm"
  ],
  "input-size": "test",
  "repetitions": 15,
  "concurrent-invocations": 5,
  "memory-sizes": [
    128
  ]
}
```

This runs 5 parallel invocations of `110.dynamic-html` with 128MB memory, until we gather 15 samples, only considering warm invocations.
For OpenWhisk, we need to modify the storage configuration to point to our MinIO instance:

```json
jq --arg ip ${EXTERNAL_IP} --slurpfile file1 outputs/storage.json '.deployment.openwhisk.storage = $file1[0] | .deployment.openwhisk.storage.object.minio.address = ($ip + ":9011")' ../tutorial/sebs-tutorial/configs/experiment_perf_cost.json > outputs/openwhisk_experiment.json
```

Additionally, the experiment configuration should also use the custom `dockerhubRepository`.

### Run Perf-Cost Experiment

We use the `experiment` command of SeBS:

```bash
./sebs.py experiment invoke perf-cost \
    --config outputs/openwhisk_experiment.json \
    --output-dir results \
    --container-deployment
```

**Expected behavior :**

We will likely observe few rejected cold startups from the very first iteration; SeBS rejects all samples from the first warm-up batch.

```
Experiment.PerfCost-90ab Begin experiment on memory size 128
OpenWhisk-d967 Update an existing OpenWhisk action sebs-978b3035-110.dynamic-html-python-3.9.
Experiment.PerfCost-90ab Begin warm experiments
Experiment.PerfCost-90ab Invocation ada7e31ac100431aa7e31ac100a31ab6 is cold!
Experiment.PerfCost-90ab Invocation 4f9e7307520e4b6f9e7307520e2b6fc0 is cold!
Experiment.PerfCost-90ab Invocation a0ad0569f85f4f14ad0569f85f3f140b is cold!
Experiment.PerfCost-90ab Invocation b025b8dc48f44cf1a5b8dc48f4bcf134 is cold!
Experiment.PerfCost-90ab Invocation cb26825b2b334241a6825b2b33924134 is cold!
Experiment.PerfCost-90ab Processed 5 warm-up samples, ignoring these results.
Experiment.PerfCost-90ab Processed 5 samples out of 15, 0 errors
Experiment.PerfCost-90ab Processed 10 samples out of 15, 0 errors
Experiment.PerfCost-90ab Processed 15 samples out of 15, 0 errors
Experiment.PerfCost-90ab Mean 19.146333333333327 [ms], median 19.312 [ms], std 1.0565154465926605, CV 5.5181084973240875
Experiment.PerfCost-90ab Parametric CI (Student's t-distribution) 0.95 from 18.540719288220227 to 19.751947378446427, within 3.1630810692026334% of mean
Experiment.PerfCost-90ab Parametric CI (Student's t-distribution) 0.99 from 18.305775258171987 to 19.986891408494667, within 4.390177798158082% of mean
```

### Analyze Results

SeBS will create one output file for each memory and experiment configuration, e.g., in our case it will be just one file:

```bash
./sebs.py benchmark statistics results/perf-cost/warm_results_128.json
```

We should expect 15 samples:

```
Statistics Processing 15 results of warm type.
Statistics    Cloud provider measurements
Statistics    Intra-function measurements
Statistics            Measurement type function_exec, mean 1714.2666666666667, median 1654.0, std 267.68948844178067, cv 15.615393663477912.
Statistics    Client measurements
Statistics            Measurement type client_exec, mean 19146.333333333332, median 19312.0, std 1056.5154465926605, cv 5.518108497324086.
```

Similarly to a benchmark invocation, we can process results by downloading cloud provider metrics:

```bash
./sebs.py experiment process perf-cost \
    --config outputs/openwhisk_experiment.json \
    --output-dir results \
    --container-deployment
```

This will produce additional output files with `-processed` suffix.

```json
./sebs.py benchmark statistics results/perf-cost/warm_results_128-processed.json
```

There, we can find cloud provider metrics. Since we used warm invocations, we should only see execution time:

```
Statistics Processing 15 results of warm type.
Statistics    Cloud provider measurements
Statistics            Measurement type provider_exec, mean 3733.3333333333335, median 4000.0, std 771.7224601860152, cv 20.671137326411117.
```

### View Aggregated Statistics

The experiment will also create a CSV summary file with all measurements for further analysis:

```bash
head results/perf-cost/result.csv
```

Example output:

```
memory,type,is_cold,exec_time,connection_time,client_time,provider_time,mem_used
128,warm,False,2053,0.002317,17717,3000,
128,warm,False,1454,0.002453,20309,4000,
128,warm,False,1534,0.002341,20443,400
...
```

This file can be directly imported into analysis tools (e.g., pandas, R, Excel).

We do not have any data for `mem_used`, as this metric is not currently supported in OpenWhisk.

### Optional: Run with Cold Starts

To measure cold starts, add `cold` benchmark scenario to the experiment in `experiments.perf-cost.experiments`.

```bash
# Create config without warm_invocations flag
jq 'del(.experiments.warm_invocations)' \
    configs/experiment_perf_cost.json \
    > configs/experiment_perf_cost_cold.json

# Run experiment (takes longer due to eviction waits)
./sebs.py experiment invoke perf-cost \
    --config configs/experiment_perf_cost_cold.json \
    --deployment openwhisk \
    --output-dir results/perf-cost-cold
```

This experiment can be executed in cloud platforms, but it can take significantly longer as SeBS must wait for container evictions between invocations.

---

## Cleanup

### Stop Storage

Stop object storage.

```bash
./sebs.py storage stop object outputs/storage_ow.json
```

**Verify:**
```bash
docker ps | grep minio
```
Expected: Empty (no MinIO container)

### Delete OpenWhisk Cluster

```bash
kind delete cluster
```

Verify with this command. Expected: rror (no cluster)

```bash
kubectl get nodes
```

## Summary

In this hands-on session, we installed all necessary components to deploy a fully functional FaaS platform on a local system, running in a minimal Kubernetes environment.
We invoked SeBS benchmarks on the platform, downloaded invocation metrics from the FaaS system, and redeployed the function implemented in a different programming language.
Then, we implemented a new benchmark function based on the existing one, modified it to include additional logging and measurements, and deployed it to the platform.
Finally, we executed an automatic experiment to measure function performance under warm start conditions.

