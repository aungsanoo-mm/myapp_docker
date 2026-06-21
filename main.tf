terraform {
  required_providers {
    docker = {
      source = "kreuzwerker/docker"
      version = "3.5.0"
    }
  }
}

provider "docker" {
  # host  = "unix:///var/run/docker.sock"
}
#Docker network
data "docker_network" "myapp" {
  name = "myapp"
  
}

#pull the app image
resource "docker_image" "mydb" {
  name  = "postgres:15"
} 
resource "docker_container" "db" {
  image  = docker_image.mydb.image_id
  name   = "db"
  networks_advanced {
    name = data.docker_network.myapp.name
    ipv4_address = "172.19.0.101"
  }
  ports {
    internal = 5432
    external = 5432 

}

  env = [
    "POSTGRES_USER=postgres",
    "POSTGRES_PASSWORD=Password!",
    "POSTGRES_DB=expenses"
  ]
  volumes {
    host_path      = "/var/lib/postgresql/data"
    container_path = "/var/lib/postgresql/data"
  }
}
#pull the app image
# resource "docker_image" "mywebapp" {
#   name  = "docker-demo:local"
# } 

# 1. Tell Terraform to pull the image from GitHub Packages
resource "docker_image" "webapp" {
  # Replace with your actual github username and repo name (must be lowercase)
  name = "ghcr.io/aungsanoo-mm/myapp_docker/mywebapp:v1"
}

# 2. Deploy the container using the pulled image
resource "docker_container" "webapp" {
  name  = "mywebapp"
  image = docker_image.webapp.image_id

# #creation a container
# resource "docker_container" "webapp" {
#   image = docker_image.mywebapp.image_id
#   name  = "mywebapp" 
  networks_advanced {
    name = data.docker_network.myapp.name
    ipv4_address = "172.19.0.100"
  }
  ports {
    internal = 5000
    external = 5000
  }
  env = [
    "DATABASE_URL=postgresql://postgres:Password!@db:5432/expenses"
    
    ]
  depends_on = [docker_container.db]
}