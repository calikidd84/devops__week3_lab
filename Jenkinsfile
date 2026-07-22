pipeline {
  agent any

  environment {
    OPENROUTER_API_KEY = credentials('OPENROUTER_API_KEY')
    GH_TOKEN           = credentials('github-token')
    REPO               = 'calikidd84/devops__week3_lab'
    BASE_BRANCH        = 'main'
    MODEL              = 'google/gemini-2.0-flash-exp:free'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Install dependencies') {
      steps {
        sh 'pip install pytest openai PyGithub'
      }
    }

    stage('Test') {
      steps {
        script {
          def rc = sh(
            script: 'pytest tests/ --tb=short > build_log.txt 2>&1',
            returnStatus: true
          )

          sh 'cat build_log.txt'
          env.TESTS_FAILED = (rc != 0) ? 'true' : 'false'
        }
      }
    }

    stage('Agent: open PR') {
      when {
        expression { env.TESTS_FAILED == 'true' }
      }
      steps {
        sh 'python scripts/build_fixer_agent.py'
      }
    }

    stage('Human approval gate') {
      when {
        expression { env.TESTS_FAILED == 'true' }
      }
      steps {
        timeout(time: 60, unit: 'MINUTES') {
          input message: 'Agent opened a PR. Review it on GitHub, then Proceed or Abort.'
        }
      }
    }
  }

  post {
    always {
      archiveArtifacts artifacts: 'build_log.txt', allowEmptyArchive: true
    }
  }
}