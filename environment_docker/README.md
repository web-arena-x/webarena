# Docker for WebArena Websites
This REAME file host the instructions for our Docker images and quick start guide for starting up websites used in WebArena.

# Table of Content
- [Pre-installed Amazon Machine Image (Recommended)](#pre-installed-amazon-machine-image-recommended)
   * [Environment reset](#environment-reset)
- [Individual Website](#individual-website)
   * [Shopping Website (OneStopShop)](#shopping-website-onestopshop)
   * [E-commerce Content Management System (CMS)](#e-commerce-content-management-system-cms)
   * [Social Forum Website (Reddit)](#social-forum-website-reddit)
   * [Gitlab Website](#gitlab-website)
   * [Wikipedia Website](#wikipedia-website)
   * [Homepage](#homepage)
   * [Map](#map)
   * [Documentation sites](#documentation-sites)

## Pre-installed Amazon Machine Image (Recommended)
We provide AMI which have all the websites pre-installed. You can use the AMI to start a new EC2 instance.

```
AMI Information: find in console, EC2 - AMI Catalog
Region: us-east-2
Name: webarena
ID: ami-06290d70feea35450
```

1. Create a security group that allows all inbound traffic.

2. Create an instance (recommended type: t3a.xlarge, 1000GB EBS root volume) from the webarena AMI. Use the security group just created and remember to select SSH key-pair.

3. Create an Elastic IP and bind to the instance to associate the instance with a static IP and hostname. Take note of the hostname, usually in the form of "ec2-xx-xx-xx-xx.us-east-2.compute.amazonaws.com". This will be used as "<your-server-hostname>" in the following commands.

4. Log into the server, start all dockers by:
```bash
docker start gitlab
docker start shopping
docker start shopping_admin
docker start forum
docker start kiwix33
cd /home/ubuntu/openstreetmap-website/
docker compose start
```

:clock1: wait ~1 min to wait all services to start

5. Run
```bash
docker exec shopping /var/www/magento2/bin/magento setup:store-config:set --base-url="http://<your-server-hostname>:7770" # no trailing /
docker exec shopping mysql -u magentouser -pMyPassword magentodb -e  'UPDATE core_config_data SET value="http://<your-server-hostname>:7770/" WHERE path = "web/secure/base_url";'
# remove the requirement to reset password
docker exec shopping_admin php /var/www/magento2/bin/magento config:set admin/security/password_is_forced 0
docker exec shopping_admin php /var/www/magento2/bin/magento config:set admin/security/password_lifetime 0
docker exec shopping /var/www/magento2/bin/magento cache:flush

docker exec shopping_admin /var/www/magento2/bin/magento setup:store-config:set --base-url="http://<your-server-hostname>:7780"
docker exec shopping_admin mysql -u magentouser -pMyPassword magentodb -e  'UPDATE core_config_data SET value="http://<your-server-hostname>:7780/" WHERE path = "web/secure/base_url";'
docker exec shopping_admin /var/www/magento2/bin/magento cache:flush

docker exec gitlab sed -i "s|^external_url.*|external_url 'http://<your-server-hostname>:8023'|" /etc/gitlab/gitlab.rb
docker exec gitlab gitlab-ctl reconfigure
```

You should be able to access your environment websites now, and stop reading.
However, if you are unable to use AWS AMI, read below to set up on your own machine.

### Environment reset
After evaluating the 812 examples, reset the environment to the initial state
```bash
# stop and remove the images
docker stop shopping_admin forum gitlab shopping
docker remove shopping_admin forum gitlab shopping
# start the images
docker run --name shopping -p 7770:80 -d shopping_final_0712
docker run --name shopping_admin -p 7780:80 -d shopping_admin_final_0719
docker run --name gitlab -d -p 8023:8023 gitlab-populated-final-port8023 /opt/gitlab/embedded/bin/runsvdir-start
docker run --name forum -p 9999:80 -d postmill-populated-exposed-withimg
<repeat the commands in step 5 above>
```

## Individual Website
We highly recommend setting up the environments with AMI introduced above, but we also list the steps to setting up individual websites below. This allows you to setup selected websites locally.


### Shopping Website (OneStopShop)

Download the image tar from the following mirrors:
- https://drive.google.com/file/d/1gxXalk9O0p9eu1YkIJcmZta1nvvyAJpA/view?usp=sharing
- https://archive.org/download/webarena-env-shopping-image
- http://metis.lti.cs.cmu.edu/webarena-images/shopping_final_0712.tar

```
docker load --input shopping_final_0712.tar
docker run --name shopping -p 7770:80 -d shopping_final_0712
# wait ~1 min to wait all services to start

docker exec shopping /var/www/magento2/bin/magento setup:store-config:set --base-url="http://<your-server-hostname>:7770" # no trailing slash
docker exec shopping mysql -u magentouser -pMyPassword magentodb -e  'UPDATE core_config_data SET value="http://<your-server-hostname>:7770/" WHERE path = "web/secure/base_url";'
docker exec shopping /var/www/magento2/bin/magento cache:flush
```
Now you can visit `http://<your-server-hostname>:7770`.


### E-commerce Content Management System (CMS)

Download the image tar from the following mirrors:
- https://drive.google.com/file/d/1See0ZhJRw0WTTL9y8hFlgaduwPZ_nGfd/view?usp=sharing
- https://archive.org/download/webarena-env-shopping-admin-image
- http://metis.lti.cs.cmu.edu/webarena-images/shopping_admin_final_0719.tar

```
docker load --input shopping_admin_final_0719.tar
docker run --name shopping_admin -p 7780:80 -d shopping_admin_final_0719
# wait ~1 min to wait all services to start

docker exec shopping_admin /var/www/magento2/bin/magento setup:store-config:set --base-url="http://<your-server-hostname>:7780" # no trailing slash
docker exec shopping_admin mysql -u magentouser -pMyPassword magentodb -e  'UPDATE core_config_data SET value="http://<your-server-hostname>:7780/" WHERE path = "web/secure/base_url";'
docker exec shopping_admin /var/www/magento2/bin/magento cache:flush
```
Now you can visit `http://<your-server-hostname>:7780/admin`.


### Social Forum Website (Reddit)

Download the image tar from the following mirrors:
- https://drive.google.com/file/d/17Qpp1iu_mPqzgO_73Z9BnFjHrzmX9DGf/view?usp=sharing
- https://archive.org/download/webarena-env-forum-image
- http://metis.lti.cs.cmu.edu/webarena-images/postmill-populated-exposed-withimg.tar

```
docker load --input postmill-populated-exposed-withimg.tar
docker run --name forum -p 9999:80 -d postmill-populated-exposed-withimg
```
Now you can visit `http://<your-server-hostname>:9999/`.


### Gitlab Website

Download the image tar from the following mirrors:
- https://drive.google.com/file/d/19W8qM0DPyRvWCLyQe0qtnCWAHGruolMR/view?usp=sharing
- https://archive.org/download/webarena-env-gitlab-image
- http://metis.lti.cs.cmu.edu/webarena-images/gitlab-populated-final-port8023.tar

```
docker load --input gitlab-populated-final-port8023.tar
docker run --name gitlab -d -p 8023:8023 gitlab-populated-final-port8023 /opt/gitlab/embedded/bin/runsvdir-start

# wait at least 5 mins for services to boot
docker exec gitlab sed -i "s|^external_url.*|external_url 'http://<your-server-hostname>:8023'|" /etc/gitlab/gitlab.rb
docker exec gitlab gitlab-ctl reconfigure
```
It might take 5 mins to start and then you can visit `http://<your-server-hostname>:8023/explore`.

### Wikipedia Website

Download the data from the following mirrors:
- https://drive.google.com/file/d/1Um4QLxi_bGv5bP6kt83Ke0lNjuV9Tm0P/view?usp=sharing
- https://archive.org/download/webarena-env-wiki-image
- http://metis.lti.cs.cmu.edu/webarena-images/wikipedia_en_all_maxi_2022-05.zim

```
docker run -d --name=wikipedia --volume=<your-path-to-downloaded-folder>/:/data -p 8888:80 ghcr.io/kiwix/kiwix-serve:3.3.0 wikipedia_en_all_maxi_2022-05.zim
```
Now you can visit `http://<your-server-hostname>:8888/wikipedia_en_all_maxi_2022-05/A/User:The_other_Kiwix_guy/Landing`.

### Homepage

The homepage lists all available websites which the agent can use to navigate to different sites.
![Homepage](../media/homepage_demo.png)

To host the homepage, first change `<your-server-hostname>` to the corresponding server hostnames in [webarena_homepage/templates/index.html](webarena-homepage/templates/index.html)
```bash
# Define your actual server hostname
YOUR_ACTUAL_HOSTNAME=""
# Remove trailing / if it exists
YOUR_ACTUAL_HOSTNAME=${YOUR_ACTUAL_HOSTNAME%/}
# Use sed to replace placeholder in the HTML file
perl -pi -e "s|<your-server-hostname>|${YOUR_ACTUAL_HOSTNAME}|g" webarena-homepage/templates/index.html
```

Then run
```
cd webarena-homepage
flask run --host=0.0.0.0 --port=4399
```
The homepage will be available at `http://<your-server-hostname>:4399`.

### Map
Please refer to the AMI setup for the map frontend setup. For most use cases this is enough.

If you wish to also set up all map backends, namely tile server, geocoding server and routing server, read along and please be aware of very large downloads and disk space requirements.

#### Tile Sever

First download http://metis.lti.cs.cmu.edu/map_server_data/osm_tile_server.tar and extract the docker volumes to your docker volume directory (default to `/var/lib/docker/volumes/`). Make sure that you have `osm-data` volume copied.

Then run the tile server:

```bash
docker run --volume=osm-data:/data/database/ --volume=osm-tiles:/data/tiles/ -p 8080:80 --detach=true overv/openstreetmap-tile-server run
```

Now you can point all occurrences to `ogma.lti.cs.cmu.edu:8080` in the frontend server directory to your own tile server.

#### Geocoding Server
First download http://metis.lti.cs.cmu.edu/map_server_data/nominatim_volumes.tar and extract the docker volumes to your docker volume directory (default to `/var/lib/docker/volumes/`). Make sure that you have `nominatim-data` and `nominatim-flatnode` volume copied.

Also download http://metis.lti.cs.cmu.edu/map_server_data/osm_dump.tar and extract the OSM dump to a host directory `/path/to/osm_dump`, which will be used in the following command.


Then run the geocoding server:
```bash
docker run --env=IMPORT_STYLE=extratags --env=PBF_PATH=/nominatim/data/us-northeast-latest.osm.pbf --env=IMPORT_WIKIPEDIA=/nominatim/data/wikimedia-importance.sql.gz --volume=/path/to/osm_dump:/nominatim/data --volume=nominatim-data:/var/lib/postgresql/14/main --volume=nominatim-flatnode:/nominatim/flatnode -p 8085:8080 mediagis/nominatim:4.2 /app/start.sh
```

Now you can point all occurrences to `metis.lti.cs.cmu.edu:8085` in the frontend server directory to your own geocoding server.

#### Routing Server

First download http://metis.lti.cs.cmu.edu/map_server_data/osrm_routing.tar and extract all the directories to your local path.
Make sure to have `/routing/path/<foot, car, bike>`, which will be used in 3 different routing endpoints.

Then run the 3 routing servers:
```bash
docker run --volume=/routing/path/foot/:/data -p 5002:5000 ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld /data/us-northeast-latest.osrm
docker run --volume=/routing/path/bike/:/data -p 5001:5000 ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld /data/us-northeast-latest.osrm
docker run --volume=/routing/path/car/:/data -p 5002:5000 ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld /data/us-northeast-latest.osrm
```

Now you can point all occurrences to `metis.lti.cs.cmu.edu:5000,5001 and 5002` to your respective 3 routing endpoints.


### Documentation sites
We are still working on dockerizing the documentation sites. As they are read-only sites and they usually don't change rapidly. It is safe to use their live sites for test purpose right now.
