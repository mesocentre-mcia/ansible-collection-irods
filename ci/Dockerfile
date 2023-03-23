FROM rockylinux:8.7.20221219

RUN dnf update -y \
  && dnf module install -y python39 \
  && dnf --enablerepo=powertools install -y git openssh-clients python39 python39-pip podman podman-docker \
  && dnf clean all


RUN python3.9 -m ensurepip --upgrade \
  && python3.9 -m pip install -U pip setuptools

RUN pip3.9 install ansible jmespath jinja2 yamllint ansible-lint molecule molecule[lint] molecule[podman] \
  && pip3.9 cache purge

RUN ansible-galaxy collection install community.general community.postgresql
