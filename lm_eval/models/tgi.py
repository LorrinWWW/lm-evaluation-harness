import torch
import transformers
from typing import Optional, Union
from lm_eval.base import BaseLM

import os
import requests
default_endpoint = os.environ.get(
    'ENDPOINT',
    'http://127.0.0.1:8080/generate'
)

def get_logprobs(prompt, endpoint=default_endpoint):
    endpoint = endpoint or default_endpoint
    res = requests.post(endpoint, json={
        "inputs": prompt,
        "parameters":{
            "max_new_tokens":1, "decoder_input_details": True
        }
    }, headers={})

    logprobs = []
    predictions = []
    res_json = res.json()
    if 'error' in res_json:
        raise Exception(res_json['error'])
    for item in res_json['details']['prefill']:
        logprobs.append(item['logprob'])
        predictions.append(item['predicted_id'])

    return logprobs, predictions
    

def _get_dtype(
    dtype: Union[str, torch.dtype]
) -> torch.dtype:
    """Converts `dtype` from `str` to torch.dtype when possible. Does not use an instantiated HF AutoConfig"""
    if isinstance(dtype, str) and dtype != "auto":
        # Convert `str` args torch dtype: `float16` -> `torch.float16`
        _torch_dtype = getattr(torch, dtype)
    else:
        _torch_dtype = dtype
    return _torch_dtype


class HFLM(BaseLM):

    _DEFAULT_MAX_LENGTH = 2048

    def __init__(
        self,
        device="cuda",
        pretrained="gpt2",
        revision="main",
        low_cpu_mem_usage=None,
        subfolder=None,
        tokenizer=None,
        batch_size=1,
        max_batch_size=512,
        max_length=None,
        load_in_8bit: Optional[bool] = False,
        trust_remote_code: Optional[bool] = False,
        dtype: Optional[Union[str, torch.dtype]]="auto",
    ):
        super().__init__()


        # Initialize model
        self._device = "cpu"
        
        # Initialize new tokenizer instances
        self.model = 'tgi'
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
                tokenizer if tokenizer else pretrained,
                revision=revision,
                trust_remote_code=trust_remote_code,
                )

        self.vocab_size = self.tokenizer.vocab_size

        # Validate batch_size
        assert isinstance(batch_size, (int, str))

        # setup for automatic batch size detection
        if str(batch_size).startswith("auto"):
            batch_size = batch_size.split(":")
            self.batch_size_per_gpu = batch_size[0]
            self.batch_schedule = float(batch_size[1]) if len(batch_size) > 1 else 1
        else:
            self.batch_size_per_gpu = int(batch_size)
        self.max_batch_size = max_batch_size

        self._max_length = max_length

        self.endpoint = default_endpoint

    @property
    def eot_token_id(self):
        # we use EOT because end of *text* is more accurate for what we're doing than end of *sentence*
        return self.tokenizer.eos_token_id

    @property
    def max_length(self):
        if self._max_length: # if max length manually set, return it
            return self._max_length
        seqlen_config_attrs = ("n_positions", "max_position_embeddings", "n_ctx")
        # for attr in seqlen_config_attrs:
        #     if hasattr(self.model.config, attr):
        #         return getattr(self.model.config, attr)
        if hasattr(self.tokenizer, "model_max_length"):
            if self.tokenizer.model_max_length == 1000000000000000019884624838656:
                return self._DEFAULT_MAX_LENGTH
            return self.tokenizer.model_max_length
        return self._DEFAULT_MAX_LENGTH


    @property
    def max_gen_toks(self):
        return 256

    @property
    def batch_size(self):
        return 1

    @property
    def device(self):
        # TODO: fix multi-gpu
        return self._device

    def tok_encode(self, string: str):
        return self.tokenizer.encode(string, add_special_tokens=False)

    def tok_decode(self, tokens):
        return self.tokenizer.decode(tokens)

    def _model_call(self, inps, texts=None):
        logprobs = []
        predictions = []
        for i in range(len(inps)):
            input_ids = inps[i]
            if texts is None or texts[i] is None:
                text = self.tok_decode(input_ids)
            else:
                text = texts[i]
            input_ids_2 = self.tok_encode(text)
            input_ids = input_ids.tolist()
            input_ids_2 = input_ids_2[:len(input_ids)]
            if input_ids != input_ids_2:
                if input_ids[2:] != input_ids_2[2:]:
                    print(input_ids[:])
                    print(input_ids_2[:])
                    raise Exception('Tokenization does not match.')
                else:
                    print('Warn: The first two tokens do not match. This is possible when doing LM evaluation, which might bring slight difference to the perplexity.')
            logprob, prediction = get_logprobs(text, self.endpoint)
            logprobs.append(logprob)
            predictions.append(prediction)
        return logprobs, predictions

    def _model_generate(self, context, max_length, eos_token_id):
        generation_kwargs = {"do_sample": False, "max_length": max_length}
        if eos_token_id is not None:
            generation_kwargs['eos_token_id'] = eos_token_id
            generation_kwargs['pad_token_id'] = eos_token_id # setting eos_token_id as pad token
        assert False


# for backwards compatibility
TGILM = HFLM
