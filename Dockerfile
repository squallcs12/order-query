ARG BUILD_ENV=dev

FROM python:3.12-slim-bullseye as build

RUN apt-get update \
&& apt-get install --no-install-recommends build-essential apt-utils procps libgdal-dev gettext curl dos2unix -y

RUN  pip install -U pip poetry \
&&  poetry config virtualenvs.create false
#&&  curl -LO https://storage.googleapis.com/kubernetes-release/release/v1.19.13/bin/linux/amd64/kubectl \
#&&  chmod +x ./kubectl \
#&&  mv ./kubectl /usr/local/bin/kubectl

WORKDIR /app
CMD ["/app/entrypoint.sh"]

ADD poetry.lock pyproject.toml ./

# prod target
FROM build AS container-prod

RUN pip install uwsgi ddtrace

COPY . .
RUN poetry install --no-dev \
&& rm -rf /root/.cache/pip/
# dev target
FROM build AS container-dev

RUN apt-get update \
&& apt-get install -y postgresql-client git zsh curl \
&& sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

COPY . .
RUN poetry install \
&& cp /app/.docker/app/.zshrc /root/.zshrc \
&& dos2unix /root/.zshrc

FROM container-${BUILD_ENV}
CMD ["/app/entrypoint.sh"]
