import React, { Component } from 'react'
import { remote } from 'electron'

import { Grid, Card, Button, Radio, Item, Icon, Label } from 'semantic-ui-react'

const mainProcess = remote.require('./server')

class Predictors extends Component {
  getField = () => (
    <Item>
      <Item.Content>
        <Item.Header>
          <h5>
            Select the directory that contains the variables that will be used to
            compute the predictors:
          </h5>
        </Item.Header>

        <Item.Description>
          <Button
            onClick={() => this.props.onPathChange(mainProcess.selectDirectory())}
          >
            Browse
          </Button>
        </Item.Description>
        <Item.Extra>
          {this.props.predictors.path && (
            <div>
              <b>Path:</b> <code>{this.props.predictors.path}</code>
            </div>
          )}
          {this.props.predictors.codes.length !== 0 && (
            <div>
              <b>Predictor short names:</b>{' '}
              {this.props.predictors.codes.map(code => (
                <Label key={code}>{code}</Label>
              ))}
            </div>
          )}
        </Item.Extra>
      </Item.Content>
    </Item>
  )

  isComplete = () => this.props.predictors.codes.length > 0

  componentDidUpdate = prevProps => {
    this.isComplete() && this.props.completeSection()
  }

  render() {
    return (
      <Grid container centered>
        <Grid.Column>
          <Card fluid color="black">
            <Card.Header>
              <Grid.Column floated="left">
                Model data — Variables to compute predictors
              </Grid.Column>
              <Grid.Column floated="right">
                {this.isComplete() && <Icon name="check circle" />}
              </Grid.Column>
            </Card.Header>
            <Card.Content>
              <Card.Description />
              <Item.Group divided>{this.getField()}</Item.Group>
            </Card.Content>
          </Card>
        </Grid.Column>
      </Grid>
    )
  }
}

export default Predictors