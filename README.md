# fastapi-gateway-svc

Gateway Service with FastAPI

## How to Run this application on Kubernetes

- Build the docker images using docker-compose file:
    `docker compose build gateway`
    `docker compose build ui`
    `docker compose build service1`

- All kubernetes deployment and service manifests available in k8s folder
- Create a namespace to keep all the services in same namespace
  `kubectl apply -f k8s/namespace.yaml`
- `.env` file contains default, tenant1 & tenant2 configurations. This file is used to create a configmap in kubernetes as gateway-env.
  `kubectl create configmap gateway-env --from-env-file=.env -n my-app-namespace`
- Create the keycloak, gateway, UI & service1 applications with below commands:
  `kubectl apply -f k8s/keycloak.yaml`
  `kubectl apply -f k8s/gateway.yaml`
  `kubectl apply -f k8s/ui.yaml`
  `kubectl apply -f k8s/service1.yaml`
- Verify all the pods are up and running in healthy state:
  `kubectl get pods -n my-app-namespace`
- Keycloak service should be accessible from localhost to add realms, clients and users. Hence use the port-forward option:
  `kubectl port-forward service/keycloak 8080:80 -n my-app-namespace`
- Login to Keycloak app at: `http://localhost:8080` with below credentials:
  - Username: admin
  - Password: admin
- Add realms:
  - fastapi-gateway -> client: fastapi-client -> user: ravi [set password]
  - tenant1 -> client: tenant1-client -> user: ravi [set password]
  - tenant2 -> client: tenant2-client -> user: ram [set password]
- copy the secrets of each above clients and add them into .env file.
- As `.env` file changed, then we need to delete the existing the configMap and re-create it.
  `kubectl delete configmap gateway-env -n my-app-namespace`
  `kubectl apply -f k8s/gateway-env.yaml -n my-app-namespace`

- Delete the Gateway pod by deleting it's deployment and re-apply the changes:
  `kubectl delete deployment gateway -n my-app-namespace`
  `kubectl apply -f k8s/gateway.yaml -n my-app-namespace`

- Verify the application by running on two differents tenant DNSs:

  - http://tenant1.restaurant:8000/ui/restaurants
  - http://tenant2.restaurant:8000/ui/restaurants

- After successful login, you should able to see the restaurant page.
