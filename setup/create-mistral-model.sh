#!/bin/bash

model_name="mistral"
custom_model_name="crew-mistral"

ollama pull $model_name

ollama create $custom_model_name -f ./setup/mistral-model-file