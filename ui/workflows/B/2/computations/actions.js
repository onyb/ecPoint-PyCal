import client from '~/utils/client'
import toast from '~/utils/toast'

export const addComputation = data => ({
  type: 'COMPUTATIONS.ADD',
  data,
})

export const updateComputationShortName = (index, shortname) => ({
  type: 'COMPUTATIONS.UPDATE_SHORT_NAME',
  index,
  shortname,
})

export const updateComputationFullName = (index, fullname) => ({
  type: 'COMPUTATIONS.UPDATE_FULL_NAME',
  index,
  fullname,
})

export const updateComputationField = (index, field) => ({
  type: 'COMPUTATIONS.UPDATE_FIELD',
  index,
  field,
})

export const updateComputationInputs = (index, inputs) => ({
  type: 'COMPUTATIONS.UPDATE_INPUTS',
  index,
  inputs,
})

export const fetchAndUpdateInputUnits = (index, input) => async dispatch => {
  await client
    .post('/get-predictor-units', { path: input.path })
    .then(response =>
      dispatch({
        type: 'COMPUTATIONS.SET_INPUT_UNITS',
        code: input.code,
        units: response.data.units,
        index,
      })
    )
    .catch(e => {
      console.error(e)
      if (e.response !== undefined) {
        console.error(`Error response: ${e.response}`)
        toast.error(`${e.response.status} ${e.response.statusText}`)
      } else {
        toast.error('Empty response from server')
      }
    })
}

export const removeComputation = index => ({
  type: 'COMPUTATIONS.REMOVE',
  index,
})

export const setScaleOp = (index, op) => ({
  type: 'COMPUTATIONS.SET_SCALE_OP',
  index,
  op,
})

export const setMulScaleValue = (index, value) => ({
  type: 'COMPUTATIONS.SET_MUL_SCALE_VALUE',
  index,
  value,
})

export const setAddScaleValue = (index, value) => ({
  type: 'COMPUTATIONS.SET_ADD_SCALE_VALUE',
  index,
  value,
})

export const appendLog = log => ({
  type: 'COMPUTATIONS.APPEND_LOG',
  log,
})

export const toggleComputationPostProcess = index => ({
  type: 'COMPUTATIONS.TOGGLE_POST_PROCESS',
  index,
})
