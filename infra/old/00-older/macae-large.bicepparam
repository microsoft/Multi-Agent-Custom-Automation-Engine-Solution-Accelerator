using './macae.bicep'

param resourceSize = {
  gpt4oCapacity: 50
  containerAppSize: {
    cpu: '2.0'
    memory: '4.0Gi'
    minReplicas: 1
    maxReplicas: 1
  }
}
