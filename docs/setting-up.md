# Setting Up

```bash
# Clone to bench/apps folder first
$ git clone git@github.com:leam-tech/renovation_core --branch v2 ./apps/renovation_core_v2

# Activate virtual-env
$ . ./env/bin/activate

# Install via pip
(env) $ pip install -e ./renovation_core_v2

# Add renovation_core to apps.txt
(env) $ echo -e -n '\nrenovation_core' >> ./sites/apps.txt

# Build js resources if any
(env) $ bench build --app renovation_core

# And install app!
(env) $ bench --site <site> install-app renovation_core
```
