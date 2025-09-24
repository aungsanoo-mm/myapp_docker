terraform {
  required_providers {
    docker = {
      source = "kreuzwerker/docker"
      version = "3.5.0"
    }
  }
}

provider "docker" {
  host  = "unix:///var/run/docker.sock"
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
    ipv4_address = "172.18.0.101"
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
resource "docker_image" "mywebapp" {
  name  = "expense-tracker:latest"
} 

#creation a container
resource "docker_container" "webapp" {
  image = docker_image.mywebapp.image_id
  name  = "mywebapp" 
  networks_advanced {
    name = data.docker_network.myapp.name
    ipv4_address = "172.18.0.100"
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