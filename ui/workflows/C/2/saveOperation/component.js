import React, { Component } from 'react'

import { Modal, Input, Button, Segment, Label, Icon } from 'semantic-ui-react'

import semver from 'semver'
import { remote } from 'electron'

import client from '~/utils/client'
import toast from '~/utils/toast'
const jetpack = require('fs-jetpack')

const mainProcess = remote.require('./server')

const defaultState = {
  family: null,
  version: null,
  accumulation: null,
  inf: 'inf',
  mfcols: null,
  outPath: null,
}

class SaveOperation extends Component {
  state = defaultState

  isEmpty = () => {
    if (this.props.mode === 'mf') {
      return !this.state.mfcols || !this.state.outPath
    } else if (this.props.mode === 'wt') {
      return !this.state.outPath
    } else if (this.props.mode === 'bias') {
      return !this.state.outPath
    } else if (
      this.props.mode === 'breakpoints' ||
      this.props.mode === 'breakpoints-upload'
    ) {
      return !this.state.inf || !this.state.outPath
    } else {
      return (
        !this.state.family ||
        !this.state.version ||
        !this.state.inf ||
        !this.state.mfcols ||
        !this.state.outPath
      )
    }
  }

  close = () => {
    this.setState(defaultState)
    this.props.onClose()
  }

  getMetadataComponent = () => (
    <Segment padded>
      <h5>Enter operation metadata:</h5>
      <Input
        label="Family*"
        placeholder="rainfall"
        value={this.state.family}
        onChange={e => this.setState({ family: e.target.value })}
      />{' '}
      <Input
        label="Version*"
        error={this.state.version && semver.valid(this.state.version) === null}
        value={this.state.version}
        onChange={e => this.setState({ version: e.target.value })}
      />{' '}
      <Input
        label="Accumulation (in hours)"
        value={this.state.accumulation}
        onChange={e => this.setState({ accumulation: e.target.value })}
      />
      <br />
      <br />
      <p>Fields marked with * are mandatory.</p>
    </Segment>
  )

  getBreakpointsCSVComponent = () => (
    <Segment padded>
      <h5>
        Enter parameters for {this.props.mode === 'breakpoints' ? 'saving' : 'loading'}{' '}
        breakpoints in Weather Types as CSV:
      </h5>
      <Input
        label="Infinity value"
        value={this.state.inf}
        onChange={e => this.setState({ inf: e.target.value })}
      />
    </Segment>
  )

  getMFsCSVComponent = () => (
    <Segment padded>
      <h5>Enter parameters for saving MFs as CSV:</h5>
      <Input
        label="No. of columns"
        value={this.state.mfcols}
        onChange={e => this.setState({ mfcols: e.target.value })}
      />
    </Segment>
  )

  getOutputPathComponent = () => (
    <Segment padded>
      <h5>Select path:</h5>
      <Button
        as="div"
        labelPosition="right"
        onClick={() => {
          let path

          if (this.props.mode === 'all' || this.props.mode === 'wt') {
            path = mainProcess.selectDirectory() || null
          } else if (this.props.mode === 'mf') {
            path = mainProcess.saveFile(`${this.props.error}.csv`) || null
          } else if (this.props.mode === 'breakpoints') {
            path = mainProcess.saveFile('BreakPointsWT.csv') || null
          } else if (this.props.mode === 'breakpoints-upload') {
            path = mainProcess.openFile() || null
          } else if (this.props.mode === 'bias') {
            path = mainProcess.saveFile('BiasesWT.csv') || null
          }

          path !== null && this.setState({ outPath: path })
        }}
      >
        <Button icon>
          <Icon name="save" />
          Browse
        </Button>
        {this.state.outPath !== null && (
          <Label basic pointing="left">
            {this.state.outPath}
          </Label>
        )}
      </Button>
    </Segment>
  )

  getHeader = () => {
    if (this.props.mode === 'mf') {
      return 'Save Mapping Functions as CSV'
    } else if (this.props.mode === 'breakpoints') {
      return 'Save Breakpoints for Weather Types as CSV'
    } else if (this.props.mode === 'breakpoints-upload') {
      return 'Upload Breakpoints CSV'
    } else if (this.props.mode === 'wt') {
      return 'Save Weather Types as PNG'
    } else if (this.props.mode === 'bias') {
      return 'Save summary of Weather Type biases'
    }

    return 'Save Operation Files'
  }

  getBreakpointsCSV = () => {
    const rows = this.props.breakpoints
      .map(row => row.map(cell => cell.replace('inf', this.state.inf)).join(','))
      .join('\n')
    return [['WT code', ...this.props.labels], rows].join('\n')
  }

  setBreakpointsCSV = () => {
    const csv = jetpack.read(this.state.outPath)
    const data = csv.split('\n').map(row => row.split(','))
    const matrix = data
      .slice(1)
      .map(row => row.slice(1))
      .map(row => row.map(cell => cell.replace(this.state.inf, 'inf')))

    this.props.setLoading('Generating and rendering decision tree.')
    this.props.setBreakpoints(this.props.labels, matrix)
    this.props.setLoading(false)
    this.close()
  }

  save = () => {
    this.props.setLoading('Saving...')
    const matrix = this.props.breakpoints.map(row => _.flatMap(row.slice(1)))

    client
      .post('/postprocessing/save', {
        labels: this.props.labels,
        yLim: this.props.yLim, // for mode === "wt"
        bins: this.props.bins, // for mode === "wt"
        thrGridOut: this.props.breakpoints,
        matrix,
        pdtPath: this.props.path,
        cheaper: this.props.cheaper,
        mode: this.props.mode,
        breakpointsCSV:
          this.props.mode === 'breakpoints' || this.props.mode === 'all'
            ? this.getBreakpointsCSV()
            : null,
        ...this.state,
      })
      .then(response => {
        toast.success('Successfully saved operation files')
        this.props.setLoading(false)
      })
      .catch(e => {
        if (e.response !== undefined) {
          const error = `(${
            e.response.status
          }) ${e.response.config.method.toUpperCase()} ${e.response.config.url}: ${
            e.response.data
          }`

          console.error(error)
          toast.error(error)
        } else {
          toast.error('Empty response from server')
        }
      })
      .then(() => {
        this.props.setLoading(false)
        this.close()
      })
  }

  render = () => {
    return (
      this.props.mode !== null && (
        <Modal size={'large'} open={this.props.open} onClose={this.close}>
          <Modal.Header>{this.getHeader()}</Modal.Header>
          <Modal.Content>
            {this.props.mode === 'all' && this.getMetadataComponent()}
            {(this.props.mode === 'all' ||
              this.props.mode === 'breakpoints' ||
              this.props.mode === 'breakpoints-upload') &&
              this.getBreakpointsCSVComponent()}
            {(this.props.mode === 'all' || this.props.mode === 'mf') &&
              this.getMFsCSVComponent()}
            {this.getOutputPathComponent()}
          </Modal.Content>
          <Modal.Actions>
            <Button
              color="green"
              icon={this.props.mode === 'breakpoints-upload' ? 'upload' : 'download'}
              content={this.props.mode === 'breakpoints-upload' ? 'Upload' : 'Save'}
              disabled={this.isEmpty()}
              onClick={() =>
                this.props.mode === 'breakpoints-upload'
                  ? this.setBreakpointsCSV()
                  : this.save()
              }
            />
          </Modal.Actions>
        </Modal>
      )
    )
  }
}

export default SaveOperation
