pipeline {
  agent any

  environment {
    OPENROUTER_API_KEY = credentials('OPENROUTER_API_KEY')
    GH_TOKEN           = credentials('github-token')
    REPO               = 'calikidd84/devops__week3_lab'
    BASE_BRANCH        = 'main'
    MODEL              = 'openrouter/free'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Debug env check') {
      steps {
        sh '''
          python - <<'EOF'
import os

print("=== Debug environment check ===")
print("OPENROUTER_API_KEY present:", bool(os.environ.get("OPENROUTER_API_KEY")))
print("GH_TOKEN present:", bool(os.environ.get("GH_TOKEN")))
print("REPO:", os.environ.get("REPO"))
print("BASE_BRANCH:", os.environ.get("BASE_BRANCH"))
print("MODEL:", os.environ.get("MODEL"))
print("OPENROUTER_API_KEY length:", len(os.environ.get("OPENROUTER_API_KEY", "")))
print("GH_TOKEN length:", len(os.environ.get("GH_TOKEN", "")))
EOF
        '''
      }
    }

    stage('Install dependencies') {
      steps {
        sh 'python -m pip install --upgrade pip'
        sh 'python -m pip install pytest openai PyGithub'
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
          echo "TESTS_FAILED=${env.TESTS_FAILED}"
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