pipeline {
    agent any

    options {
        // Le plugin declaratif fait deja un checkout : sans cette option,
        // le depot est clone deux fois a chaque build.
        skipDefaultCheckout(true)
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '15', artifactNumToKeepStr: '15'))
        timeout(time: 40, unit: 'MINUTES')
    }

    environment {
        DOCKER_HUB_REPO = "sorydiallo89/gitops-project"
        DOCKER_HUB_CREDENTIALS_ID = "gitops-dockerhub-token"
        ARGOCD_SERVER = "192.168.49.2:31679"   // minikube ip + nodePort HTTPS d'argocd-server
        ARGOCD_APP = "immobilier-idf"

        DOCKER_BUILDKIT = "1"
        TRIVY_CACHE_DIR = "/var/lib/jenkins/.cache/trivy"
        TRIVY_NO_PROGRESS = "true"
        TRIVY_DISABLE_VEX_NOTICE = "true"
    }

    stages {

        stage('Checkout Github') {
            steps {
                echo 'Checking out code from GitHub...'
                checkout scmGit(branches: [[name: '*/main']], extensions: [], userRemoteConfigs: [[credentialsId: 'github-token', url: 'https://github.com/sory89/immobilier_idf_gitops.git']])
            }
        }

        stage('Build Docker Images') {
            // Les deux images sont independantes : construction simultanee.
            parallel {
                stage('API') {
                    steps {
                        sh 'docker build -f server/Dockerfile -t ${DOCKER_HUB_REPO}:api-${BUILD_NUMBER} .'
                    }
                }
                stage('Client') {
                    steps {
                        sh 'docker build -f client/Dockerfile -t ${DOCKER_HUB_REPO}:client-${BUILD_NUMBER} .'
                    }
                }
            }
        }

        stage('Scan Trivy') {
            // Le scan precede le push : une image vulnerable ne doit pas atteindre
            // le registre. Une seule analyse par image, le JSON servant ensuite de
            // source a l'affichage et au controle bloquant (six scans auparavant).
            steps {
                sh '''
                if [ ! -x /usr/local/bin/trivy ]; then
                    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sudo sh -s -- -b /usr/local/bin
                fi

                for c in api client; do
                    trivy image --scanners vuln --format json \
                          -o "trivy-${c}.json" ${DOCKER_HUB_REPO}:${c}-${BUILD_NUMBER}
                    echo "--- Rapport ${c} (HIGH + CRITICAL) ---"
                    trivy convert --format table --severity HIGH,CRITICAL "trivy-${c}.json"
                done

                # Le build echoue uniquement sur les CRITICAL disposant d'un correctif :
                # sans --ignore-unfixed, une image Python remonte en permanence des CVE
                # systeme non corrigeables et le pipeline serait rouge en continu.
                echo "--- Controle bloquant (CRITICAL corrigeables) ---"
                trivy convert --severity CRITICAL --ignore-unfixed --exit-code 1 trivy-api.json
                trivy convert --severity CRITICAL --ignore-unfixed --exit-code 1 trivy-client.json
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
            // docker login direct plutot que docker.withRegistry : pas de retag
            // vers registry.hub.docker.com, logs allegés, et disparition de
            // l'avertissement Groovy "Did you forget the def keyword".
            steps {
                withCredentials([usernamePassword(credentialsId: "${DOCKER_HUB_CREDENTIALS_ID}",
                                                  usernameVariable: 'DH_USER',
                                                  passwordVariable: 'DH_PASS')]) {
                    sh '''
                    echo "${DH_PASS}" | docker login -u "${DH_USER}" --password-stdin

                    docker tag ${DOCKER_HUB_REPO}:api-${BUILD_NUMBER}    ${DOCKER_HUB_REPO}:api-latest
                    docker tag ${DOCKER_HUB_REPO}:client-${BUILD_NUMBER} ${DOCKER_HUB_REPO}:client-latest

                    docker push ${DOCKER_HUB_REPO}:api-${BUILD_NUMBER}
                    docker push ${DOCKER_HUB_REPO}:client-${BUILD_NUMBER}
                    docker push ${DOCKER_HUB_REPO}:api-latest
                    docker push ${DOCKER_HUB_REPO}:client-latest
                    '''
                }
            }
        }

        stage('Install Kubectl & ArgoCD CLI Setup') {
            steps {
                sh '''
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
                // Le pas kubeconfig doit rester dans un bloc script :
                // hors de ce contexte, Jenkins reclame tous ses parametres
                // (erreur "Missing required parameter: caCertificate").
                script {
                    kubeconfig(credentialsId: 'kubeconfig', serverUrl: 'https://192.168.49.2:8443') {
                        // Le cluster peut sortir d'un redemarrage : on attend que
                        // les composants ArgoCD repondent, avec une 2e tentative.
                        retry(2) {
                            sh '''
                            kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s

                            argocd login ${ARGOCD_SERVER} --username admin \
                                   --password $(kubectl get secret -n argocd argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d) \
                                   --insecure --grpc-web
                            argocd app sync ${ARGOCD_APP} --grpc-web
                            argocd app wait ${ARGOCD_APP} --health --timeout 300 --grpc-web
                            '''
                        }
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
            sh '''
            docker logout || true
            docker image prune -f --filter "until=24h" || true
            '''
        }
    }
}
