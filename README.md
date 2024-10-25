# eLxr Metrics

## Description

The eLxr Metrics project is designed to provide insights into the website performance and package distribution metrics. It tracks key indicators such as website view count and download statistics for binary packages, presenting the data in visually informative charts. The dashboard allows administrators to monitor website traffic and package popularity, ensuring effective tracking and optimization of resource delivery. For further design details, user can go to [High-Level Design Document for eLxr Metrics Collection](./hld.md).

## Getting started

This project is not designed to run manually, but to be scheduled at certain interval in the background. However for development purpose, you can setup the development environment in the following steps:

```bash
python3 -m venv venv
. venv/bin/activate
pip install --upgrade pip wheel
pip install flit
flit install -s --deps develop
```

## Usage

The project can be launched manually. After launch, the program expects 3 parameters. The first parameter is the folder that contains raw CloudFront log files (.gz). The second parameter is the target csv file that holds metrics data. The third parameter is the log type indicator. Below are some examples:

```bash
elxr-metrics logs/elxr_org/ public/elxr_org_view.csv elxr_org_view
elxr-metrics logs/mirror_elxr_dev/ public/package_stats.csv package_download
elxr-metrics log_path=logs/elxr_org/ csv_path=public/elxr_org_view.csv log_type=elxr_org_view
elxr-metrics log_path=logs/mirror_elxr_dev/ csv_path=public/package_stats.csv log_type=package_download
```

After execution, the csv file should be refreshed with the new metrics data from log files. User can open the [index.html](./public/index.html) in a browser to verify the metrics.

## Deployment

The latest metrics page can be accessible via [GitLab Pages](https://elxr-metrics-d8932f.gitlab.io/) or [eLxr website](https://elxr.org/metrics/)

## Reference

- [Python Package Template](https://github.com/microsoft/python-package-template)
- [aws-log-parser](https://github.com/dpetzold/aws-log-parser/)
- [Chart.js](https://www.chartjs.org/)
