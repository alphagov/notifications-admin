#!groovy

def deploy(cfEnv) {
  buildJobWithRetry("deploy-notify-admin-paas-${cfEnv}", [
    [$class: 'StringParameterValue', name: 'DEPLOY_BUILD_NUMBER', value: env.BUILD_NUMBER]
  ])
  node {
    checkout scm
    sh("git tag -f deployed-to-cf-${cfEnv} ${gitCommit}")
    sh("git push -f origin deployed-to-cf-${cfEnv}")
  }
}

def buildJobWithRetry(jobName, jobParameters=[]) {
  waitUntil {
    try {
      build job: jobName, parameters: jobParameters
      true
    } catch(err) {
      echo "${jobName} failed: ${err}"
      try {
        slackSend channel: '#govuk-notify', message: "${jobName} failed. Please retry or abort: <${env.BUILD_URL}|${env.JOB_NAME} - #${env.BUILD_NUMBER}>", color: 'danger'
      } catch(err2) {
        echo "Sending Slack message failed: ${err2}"
      }
      input "${jobName} failed. Retry?"
      false
    }
  }
}

try {
  node {
    stage('Build') {
      git url: 'git@github.com:alphagov/notifications-admin.git', branch: 'master', credentialsId: 'github_com_and_gds'
      checkout scm

      gitCommit = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()

      milestone 10
      withEnv(["PIP_ACCEL_CACHE=${env.JENKINS_HOME}/cache/pip-accel"]) {
        sh 'make cf-build-with-docker'
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
          sh 'make coverage-with-docker'
        }
      } catch(err) {
        echo "Coverage failed: ${err}"
      }
    }

    stage('Upload') {
      milestone 30
      sh 'make build-paas-artifact upload-paas-artifact'
    }
  }

  stage('Preview') {
    if (deployToPreview == "true") {
      milestone 40
      deploy 'preview'
      buildJobWithRetry('notify-functional-tests-preview', [
        [$class: 'StringParameterValue', 'name': 'NOTIFY_ADMIN_URL', 'value': 'https://admin-paas.notify.works'],
        [$class: 'StringParameterValue', 'name': 'NOTIFY_API_URL', 'value': 'https://api-paas.notify.works']
      ])
    } else {
      echo 'Preview skipped.'
    }
  }

  stage('Staging') {
    if (deployToStaging == "true") {
      milestone 50
      input 'Approve?'
      deploy 'staging'
      buildJobWithRetry('notify-functional-tests-staging', [
        [$class: 'StringParameterValue', 'name': 'NOTIFY_ADMIN_URL', 'value': 'https://admin-paas.staging-notify.works'],
        [$class: 'StringParameterValue', 'name': 'NOTIFY_API_URL', 'value': 'https://api-paas.staging-notify.works']
      ])
    } else {
      echo 'Staging skipped.'
    }
  }

  stage('Prod') {
    if (deployToProduction == "true") {
      milestone 60
      input 'Approve?'
      deploy 'production'
      buildJobWithRetry('notify-functional-admin-tests-production', [
        [$class: 'StringParameterValue', 'name': 'NOTIFY_ADMIN_URL', 'value': 'https://admin-paas.notifications.service.gov.uk'],
        [$class: 'StringParameterValue', 'name': 'NOTIFY_API_URL', 'value': 'https://api-paas.notifications.service.gov.uk']
      ])
      buildJobWithRetry('notify-functional-api-email-test-production', [
        [$class: 'StringParameterValue', 'name': 'NOTIFY_ADMIN_URL', 'value': 'https://admin-paas.notifications.service.gov.uk'],
        [$class: 'StringParameterValue', 'name': 'NOTIFY_API_URL', 'value': 'https://api-paas.notifications.service.gov.uk']
      ])
      buildJobWithRetry('notify-functional-api-sms-test-production', [
        [$class: 'StringParameterValue', 'name': 'NOTIFY_ADMIN_URL', 'value': 'https://admin-paas.notifications.service.gov.uk'],
        [$class: 'StringParameterValue', 'name': 'NOTIFY_API_URL', 'value': 'https://api-paas.notifications.service.gov.uk']
      ])
    } else {
      echo 'Production skipped.'
    }
  }
} catch (org.jenkinsci.plugins.workflow.steps.FlowInterruptedException fie) {
  currentBuild.result = 'ABORTED'
} catch (err) {
  currentBuild.result = 'FAILURE'
  echo "Pipeline failed: ${err}"
  slackSend channel: '#govuk-notify', message: "${env.JOB_NAME} - #${env.BUILD_NUMBER} failed (<${env.BUILD_URL}|Open>)", color: 'danger'
} finally {
  node {
    try {
      step([$class: 'Mailer', notifyEveryUnstableBuild: true, recipients: 'notify-support+jenkins@digital.cabinet-office.gov.uk', sendToIndividuals: false])
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
