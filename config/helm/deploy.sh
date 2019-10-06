#!/bin/bash
set -eu # exit on failure, fail on unset variables

# configure context for kubernetes
kubectl config set-credentials user --token=${K8S_TOKEN}
kubectl config set-cluster cluster --server=${K8S_HOST} --insecure-skip-tls-verify=true
kubectl config set-context deploy-context --cluster=cluster --user=user --namespace=${K8S_NAMESPACE}
kubectl config use-context deploy-context

function deploy() {
 set +e
  RELEASE=${K8S_NAMESPACE};

  helm tiller run ${K8S_NAMESPACE} -- helm upgrade \
    --atomic --install --debug \
    --set image.tag=${IMAGE_TAG} \
    --set config.version=$(git describe --abbrev=0) \
    "${RELEASE}" "${CHART_PATH}" \
    -f ${CHART_PATH}/values.yaml
}
deploy;
