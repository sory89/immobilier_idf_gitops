pipeline {
    agent any
    environment {
        DOCKER_HUB_REPO = "sorydiallo89/gitops-project"
        DOCKER_HUB_CREDENTIALS_ID = "gitops-dockerhub-token"
        ARGOCD_SERVER = "192.168.49.2:31679"   // minikube ip + nodePort HTTPS d'argocd-server
        ARGOCD_APP = "immobilier-idf"
    }
    stages {
        stage('Checkout Github') {
            steps {
                echo 'Checking out code from GitHub...'
                checkout scmGit(branches: [[name: '*/main']], extensions: [], userRemoteConfigs: [[credentialsId: 'github-token', url: 'https://github.com/sory89/immobilier_idf_gitops.git']])
            }
        }
        stage('Build Docker Images') {
            steps {
                script {
                    echo 'Building Docker images (API + client)...'
                    // Contexte de build = racine du depot : les Dockerfile copient server/ ET client/
                    apiImage = docker.build("${DOCKER_HUB_REPO}:api-${BUILD_NUMBER}", "-f server/Dockerfile .")
                    clientImage = docker.build("${DOCKER_HUB_REPO}:client-${BUILD_NUMBER}", "-f client/Dockerfile .")
                }
            }
        }
        stage('Push Images to DockerHub') {
            steps {
                script {
                    echo 'Pushing Docker images to DockerHub...'
                    docker.withRegistry('https://registry.hub.docker.com', "${DOCKER_HUB_CREDENTIALS_ID}") {
                        apiImage.push("api-${BUILD_NUMBER}")
                        apiImage.push('api-latest')
                        clientImage.push("client-${BUILD_NUMBER}")
                        clientImage.push('client-latest')
                    }
                }
            }
        }
        stage('Install Kubectl & ArgoCD CLI Setup') {
            steps {
                sh '''
                echo 'installing Kubectl & ArgoCD cli...'
                if [ ! -x /usr/local/bin/kubectl ]; then
                    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
                    chmod +x kubectl
                    sudo mv kubectl /usr/local/bin/kubectl
                fi
                if [ ! -x /usr/local/bin/argocd ]; then
                    sudo curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
                    sudo chmod +x /usr/local/bin/argocd
                fi
                '''
            }
        }
        stage('Apply Kubernetes & Sync App with ArgoCD') {
            steps {
                script {
                    kubeconfig(credentialsId: 'kubeconfig', serverUrl: 'https://192.168.49.2:8443') {
                        sh '''
                        argocd login ${ARGOCD_SERVER} --username admin --password $(kubectl get secret -n argocd argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d) --insecure --grpc-web
                        argocd app sync ${ARGOCD_APP} --grpc-web
                        argocd app wait ${ARGOCD_APP} --health --timeout 300 --grpc-web
                        '''
                    }
                }
            }
        }
    }
}
