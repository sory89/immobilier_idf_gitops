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

        stage('Scan Trivy') {
            steps {
                // Le scan precede le push : une image vulnerable ne doit pas
                // atteindre le registre.
                sh '''
                echo 'Scan de securite des images...'
                if [ ! -x /usr/local/bin/trivy ]; then
                    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sudo sh -s -- -b /usr/local/bin
                fi
                trivy --version

                echo "--- Rapport API ---"
                trivy image --severity HIGH,CRITICAL --no-progress --scanners vuln \
                      ${DOCKER_HUB_REPO}:api-${BUILD_NUMBER}

                echo "--- Rapport client ---"
                trivy image --severity HIGH,CRITICAL --no-progress --scanners vuln \
                      ${DOCKER_HUB_REPO}:client-${BUILD_NUMBER}

                echo "--- Rapports HTML archives ---"
                trivy image --format json --no-progress --scanners vuln \
                      -o trivy-api.json    ${DOCKER_HUB_REPO}:api-${BUILD_NUMBER}
                trivy image --format json --no-progress --scanners vuln \
                      -o trivy-client.json ${DOCKER_HUB_REPO}:client-${BUILD_NUMBER}

                # Le build echoue uniquement sur les CRITICAL disposant d'un correctif :
                # sans --ignore-unfixed, une image Python remonte en permanence des CVE
                # systeme non corrigeables et le pipeline serait rouge en continu.
                echo "--- Controle bloquant (CRITICAL corrigeables) ---"
                trivy image --severity CRITICAL --ignore-unfixed --exit-code 1 \
                      --no-progress --scanners vuln ${DOCKER_HUB_REPO}:api-${BUILD_NUMBER}
                trivy image --severity CRITICAL --ignore-unfixed --exit-code 1 \
                      --no-progress --scanners vuln ${DOCKER_HUB_REPO}:client-${BUILD_NUMBER}
                echo "Aucune vulnerabilite critique corrigeable"
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'trivy-*.json', allowEmptyArchive: true
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
                        # Le cluster peut sortir d'un redemarrage : on attend que les
                        # composants ArgoCD soient prets avant de tenter la synchronisation.
                        kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s

                        argocd login ${ARGOCD_SERVER} --username admin --password $(kubectl get secret -n argocd argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d) --insecure --grpc-web
                        argocd app sync ${ARGOCD_APP} --grpc-web
                        argocd app wait ${ARGOCD_APP} --health --timeout 300 --grpc-web
                        '''
                    }
                }
            }
        }
    }

    post {
        success {
            echo "Build #${BUILD_NUMBER} : images api-${BUILD_NUMBER} et client-${BUILD_NUMBER} publiees"
        }
        failure {
            echo "Echec du build #${BUILD_NUMBER} - rien n'a ete deploye"
        }
        always {
            sh 'docker image prune -f --filter "until=24h" || true'
        }
    }
}
