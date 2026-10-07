# terraform plan/apply -var-file=localstack.tfvars -> LocalStack on :4566
# LocalStack ships a few mock AMIs; pick one with:
#   aws --endpoint-url=http://localhost:4566 ec2 describe-images --owners amazon
use_localstack = true
ami_id         = "ami-03cf127a"
