import { connect } from 'react-redux'

import PredictantsComponent from './component'

const mapStateToProps = state => ({
  predictant: state.predictant,
  parameters: state.parameters,
  computations: state.computations,
  page: state.page.page
})

export default connect(
  mapStateToProps
)(PredictantsComponent)
