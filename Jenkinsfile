#!groovy

def deploy(cfEnv) {
  waitUntil {
    try {
      lock(cfEnv) {
        withCredentials([
          string(credentialsId: 'paas_username', variable: 'CF_USERNAME'),
          string(credentialsId: 'paas_password', variable: 'CF_PASSWORD')
        ]) {
          withEnv(["CF_SPACE=${cfEnv}"]) {
            sh 'make cf-deploy-with-docker'
          }
        }
        gitCommit = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
        sh("git tag -f deployed-to-cf-${cfEnv} ${gitCommit}")
        sh("git push -f origin deployed-to-cf-${cfEnv}")
      }
      true
    } catch(err) {
      echo "Deployment to ${cfEnv} failed: ${err}"
      try {
        //slackSend channel: '#govuk-notify', message: "Deployment to ${cfEnv} failed. Please retry or abort: <${env.BUILD_URL}|${env.JOB_NAME} - #${env.BUILD_NUMBER}>", color: 'danger'
      } catch(err2) {
        echo "Sending Slack message failed: ${err2}"
      }
      input "Stage failed. Retry?"
      false
    }
  }
}

try {
  node {
    stage('Build') {
      git url: 'git@github.com:alphagov/notifications-admin.git', branch: 'cloudfoundry', credentialsId: 'github_com_and_gds'
      //checkout scm

      milestone 10
      withEnv(["PIP_ACCEL_CACHE=${env.JENKINS_HOME}/cache/pip-accel"]) {
        sh 'make build-with-docker'
      }
    }

    stage('Test') {
      milestone 20
      sh 'make test-with-docker'

      try {
        junit 'test_results.xml'
      } catch(err) {
        echo "Collecting jUnit results failed: ${err}"
      }

      try {
        withCredentials([string(credentialsId: 'coveralls_repo_token_api', variable: 'COVERALLS_REPO_TOKEN')]) {
          withEnv(["GIT_BRANCH=${env.GIT_BRANCH.replaceAll('origin/', '')}"]) {
            sh 'make coverage-with-docker'
          }
        }
      } catch(err) {
        echo "Coverage failed: ${err}"
      }
    }

    stage('Preview') {
      if (deployToPreview == "true") {
        milestone 30
        deploy('preview')
      } else {
        echo 'Preview skipped.'
      }
    }

    stage('Preview tests') {
      if (deployToPreview == "true") {
        build job: 'notify-functional-tests-preview'
      } else {
        echo 'Preview tests skipped.'
      }
    }

    stash name: 'source', excludes: 'node_modules/**,venv/**,wheelhouse/**', useDefaultExcludes: false
  }

  stage('Staging') {
    if (deployToStaging == "true") {
      input 'Approve?'
      milestone 40
      node {
        unstash 'source'
        deploy('staging')
      }
    } else {
      echo 'Staging skipped.'
    }
  }

  stage('Staging tests') {
    if (deployToStaging == "true") {
      build job: 'notify-functional-tests-staging'
    } else {
      echo 'Staging tests skipped'
    }
  }

  stage('Prod') {
    if (deployToProduction == "true") {
      input 'Approve?'
      milestone 50
      node {
        unstash 'source'
        deploy('production')
      }
    } else {
      echo 'Production skipped.'
    }
  }

  stage('Prod tests') {
    if (deployToProduction == "true") {
      build job: 'notify-functional-admin-tests-production'
      build job: 'notify-functional-api-email-test-production'
      build job: 'notify-functional-api-sms-test-production'
    } else {
      echo 'Production tests skipped.'
    }
  }
} catch (org.jenkinsci.plugins.workflow.steps.FlowInterruptedException fie) {
  currentBuild.result = 'ABORTED'
} catch (err) {
  currentBuild.result = 'FAILURE'
  echo "Pipeline failed: ${err}"
  //slackSend channel: '#govuk-notify', message: "${env.JOB_NAME} - #${env.BUILD_NUMBER} failed (<${env.BUILD_URL}|Open>)", color: 'danger'
} finally {
  node {
    try {
      //step([$class: 'Mailer', notifyEveryUnstableBuild: true, recipients: 'notify-support+jenkins@digital.cabinet-office.gov.uk', sendToIndividuals: false])
    } catch(err) {
      echo "Sending email failed: ${err}"
    }

    try {
      sh 'make clean-docker-containers'
    } catch(err) {
      echo "Cleaning up Docker containers failed: ${err}"
    }
  }
}
