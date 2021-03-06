import { arrayMove } from 'react-sortable-hoc'

export const setFields = fields => ({
  type: 'POSTPROCESSING.SET_FIELDS',
  data: fields,
})

export const onFieldsSortEnd = (fields, oldIndex, newIndex) => async dispatch => {
  await dispatch(setFields(arrayMove(fields, oldIndex, newIndex)))
}
