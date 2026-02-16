using './macae.bicep'

param resourceSize = {
  gpt4oCapacity: 15
  containerAppSize: {
    cpu: '1.0'
    memory: '2.0Gi'
    minReplicas: 0
    maxReplicas: 1
  }
}
