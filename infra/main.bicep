targetScope = 'resourceGroup'

param environmentName string = 'motogp-env'
param routeName string = 'paddock'

@description('Preserve existing route bindings when validating an already-bound route. The cutover script manages hostname migration.')
param customDomains array

resource environment 'Microsoft.App/managedEnvironments@2026-07-01' existing = {
  name: environmentName
}

resource route 'Microsoft.App/managedEnvironments/httpRouteConfigs@2026-07-01' = {
  parent: environment
  name: routeName
  properties: {
    rules: loadJsonContent('paddock-route.json').rules
    customDomains: customDomains
  }
}
