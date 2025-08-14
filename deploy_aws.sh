#!/bin/bash

# TuneGenie - AWS Deployment Script
# This script automates the deployment of TuneGenie to AWS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="tunegenie"
REGION="us-east-1"
INSTANCE_TYPE="t3.medium"
KEY_NAME="tunegenie-key"
SECURITY_GROUP_NAME="tunegenie-sg"
VPC_CIDR="10.0.0.0/16"
SUBNET_CIDR="10.0.1.0/24"

echo -e "${BLUE}🎵 TuneGenie AWS Deployment Script${NC}"
echo "=========================================="

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install it first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# Function to create VPC
create_vpc() {
    echo -e "${BLUE}🌐 Creating VPC...${NC}"
    
    VPC_ID=$(aws ec2 create-vpc \
        --cidr-block $VPC_CIDR \
        --query 'Vpc.VpcId' \
        --output text \
        --region $REGION)
    
    aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=$APP_NAME-vpc
    echo -e "${GREEN}✅ VPC created: $VPC_ID${NC}"
    
    # Enable DNS support
    aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support
    aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames
    
    return $VPC_ID
}

# Function to create Internet Gateway
create_internet_gateway() {
    echo -e "${BLUE}🌍 Creating Internet Gateway...${NC}"
    
    IGW_ID=$(aws ec2 create-internet-gateway \
        --query 'InternetGateway.InternetGatewayId' \
        --output text \
        --region $REGION)
    
    aws ec2 create-tags --resources $IGW_ID --tags Key=Name,Value=$APP_NAME-igw
    echo -e "${GREEN}✅ Internet Gateway created: $IGW_ID${NC}"
    
    return $IGW_ID
}

# Function to create subnet
create_subnet() {
    local vpc_id=$1
    local igw_id=$2
    
    echo -e "${BLUE}🔗 Creating Subnet...${NC}"
    
    SUBNET_ID=$(aws ec2 create-subnet \
        --vpc-id $vpc_id \
        --cidr-block $SUBNET_CIDR \
        --availability-zone ${REGION}a \
        --query 'Subnet.SubnetId' \
        --output text \
        --region $REGION)
    
    aws ec2 create-tags --resources $SUBNET_ID --tags Key=Name,Value=$APP_NAME-subnet
    echo -e "${GREEN}✅ Subnet created: $SUBNET_ID${NC}"
    
    return $SUBNET_ID
}

# Function to create route table
create_route_table() {
    local vpc_id=$1
    local igw_id=$2
    local subnet_id=$3
    
    echo -e "${BLUE}🛣️ Creating Route Table...${NC}"
    
    ROUTE_TABLE_ID=$(aws ec2 create-route-table \
        --vpc-id $vpc_id \
        --query 'RouteTable.RouteTableId' \
        --output text \
        --region $REGION)
    
    aws ec2 create-tags --resources $ROUTE_TABLE_ID --tags Key=Name,Value=$APP_NAME-rt
    
    # Add route to internet gateway
    aws ec2 create-route \
        --route-table-id $ROUTE_TABLE_ID \
        --destination-cidr-block 0.0.0.0/0 \
        --gateway-id $igw_id
    
    # Associate subnet with route table
    aws ec2 associate-route-table \
        --subnet-id $subnet_id \
        --route-table-id $ROUTE_TABLE_ID
    
    echo -e "${GREEN}✅ Route Table created and configured: $ROUTE_TABLE_ID${NC}"
}

# Function to create security group
create_security_group() {
    local vpc_id=$1
    
    echo -e "${BLUE}🔒 Creating Security Group...${NC}"
    
    SG_ID=$(aws ec2 create-security-group \
        --group-name $SECURITY_GROUP_NAME \
        --description "Security group for TuneGenie application" \
        --vpc-id $vpc_id \
        --query 'GroupId' \
        --output text \
        --region $REGION)
    
    # Add inbound rules
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 8501 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    echo -e "${GREEN}✅ Security Group created: $SG_ID${NC}"
    
    return $SG_ID
}

# Function to create EC2 instance
create_ec2_instance() {
    local subnet_id=$1
    local sg_id=$2
    
    echo -e "${BLUE}🖥️ Creating EC2 Instance...${NC}"
    
    # Check if key pair exists, create if not
    if ! aws ec2 describe-key-pairs --key-names $KEY_NAME --region $REGION &> /dev/null; then
        echo -e "${YELLOW}⚠️ Key pair $KEY_NAME not found. Creating...${NC}"
        aws ec2 create-key-pair \
            --key-name $KEY_NAME \
            --query 'KeyMaterial' \
            --output text \
            --region $REGION > ${KEY_NAME}.pem
        
        chmod 400 ${KEY_NAME}.pem
        echo -e "${GREEN}✅ Key pair created: ${KEY_NAME}.pem${NC}"
    fi
    
    # Get latest Ubuntu AMI
    AMI_ID=$(aws ssm get-parameters \
        --names /aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id \
        --query 'Parameters[0].Value' \
        --output text \
        --region $REGION)
    
    # Create EC2 instance
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $AMI_ID \
        --count 1 \
        --instance-type $INSTANCE_TYPE \
        --key-name $KEY_NAME \
        --security-group-ids $sg_id \
        --subnet-id $subnet_id \
        --associate-public-ip-address \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$APP_NAME-instance}]" \
        --query 'Instances[0].InstanceId' \
        --output text \
        --region $REGION)
    
    echo -e "${GREEN}✅ EC2 Instance created: $INSTANCE_ID${NC}"
    
    # Wait for instance to be running
    echo -e "${BLUE}⏳ Waiting for instance to be running...${NC}"
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION
    
    # Get public IP
    PUBLIC_IP=$(aws ec2 describe-instances \
        --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text \
        --region $REGION)
    
    echo -e "${GREEN}✅ Instance is running with IP: $PUBLIC_IP${NC}"
    
    return $INSTANCE_ID
}

# Function to deploy application
deploy_application() {
    local public_ip=$1
    
    echo -e "${BLUE}🚀 Deploying TuneGenie application...${NC}"
    
    # Wait for SSH to be available
    echo -e "${BLUE}⏳ Waiting for SSH to be available...${NC}"
    while ! nc -z $public_ip 22; do
        sleep 5
    done
    
    # Create deployment script
    cat > deploy_app.sh << 'EOF'
#!/bin/bash
set -e

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create application directory
mkdir -p /home/ubuntu/tunegenie
cd /home/ubuntu/tunegenie

# Create .env file (you'll need to fill this with actual values)
cat > .env << 'ENVEOF'
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
SPOTIFY_REDIRECT_URI=http://your_domain_or_ip:8501/callback
OPENAI_API_KEY=your_openai_api_key_here
COLLABORATIVE_FILTERING_ALGORITHM=SVD
LLM_TEMPERATURE=0.7
DEBUG=False
LOG_LEVEL=INFO
ENVEOF

# Clone or copy application files here
# For now, we'll create a simple test file
echo "TuneGenie application will be deployed here" > README.md

# Start application with Docker Compose
sudo docker-compose up -d

echo "TuneGenie deployment completed!"
EOF
    
    # Copy deployment script to instance
    scp -i ${KEY_NAME}.pem -o StrictHostKeyChecking=no deploy_app.sh ubuntu@$public_ip:~/
    
    # Execute deployment script
    ssh -i ${KEY_NAME}.pem -o StrictHostKeyChecking=no ubuntu@$public_ip "chmod +x deploy_app.sh && ./deploy_app.sh"
    
    echo -e "${GREEN}✅ Application deployment initiated${NC}"
}

# Function to create load balancer (optional)
create_load_balancer() {
    local subnet_id=$1
    local sg_id=$2
    
    echo -e "${BLUE}⚖️ Creating Application Load Balancer...${NC}"
    
    ALB_ARN=$(aws elbv2 create-load-balancer \
        --name $APP_NAME-alb \
        --subnets $subnet_id \
        --security-groups $sg_id \
        --query 'LoadBalancers[0].LoadBalancerArn' \
        --output text \
        --region $REGION)
    
    echo -e "${GREEN}✅ Load Balancer created: $ALB_ARN${NC}"
    
    return $ALB_ARN
}

# Main deployment function
main() {
    echo -e "${BLUE}🚀 Starting TuneGenie AWS deployment...${NC}"
    
    # Create infrastructure
    VPC_ID=$(create_vpc)
    IGW_ID=$(create_internet_gateway)
    SUBNET_ID=$(create_subnet $VPC_ID $IGW_ID)
    create_route_table $VPC_ID $IGW_ID $SUBNET_ID
    SG_ID=$(create_security_group $VPC_ID)
    INSTANCE_ID=$(create_ec2_instance $SUBNET_ID $SG_ID)
    
    # Get public IP
    PUBLIC_IP=$(aws ec2 describe-instances \
        --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text \
        --region $REGION)
    
    # Deploy application
    deploy_application $PUBLIC_IP
    
    # Create load balancer (optional)
    # ALB_ARN=$(create_load_balancer $SUBNET_ID $SG_ID)
    
    echo -e "${GREEN}🎉 TuneGenie deployment completed successfully!${NC}"
    echo -e "${BLUE}📱 Application URL: http://$PUBLIC_IP:8501${NC}"
    echo -e "${BLUE}🔑 SSH Command: ssh -i ${KEY_NAME}.pem ubuntu@$PUBLIC_IP${NC}"
    echo -e "${YELLOW}⚠️ Remember to:${NC}"
    echo -e "${YELLOW}   1. Update the .env file with your actual API credentials${NC}"
    echo -e "${YELLOW}   2. Copy your application files to the instance${NC}"
    echo -e "${YELLOW}   3. Restart the application with: docker-compose up -d${NC}"
}

# Check if script is run with correct arguments
if [ "$1" == "--help" ]; then
    echo "Usage: $0 [--help]"
    echo "Deploys TuneGenie to AWS with all necessary infrastructure"
    exit 0
fi

# Run main function
main "$@"
