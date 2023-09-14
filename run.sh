

# task=hellaswag
# export ENDPOINT=http://127.0.0.1:8060/generate && \
# python -u main.py \
#     --model tgi \
#     --model_args pretrained=/dev/shm/data/CodeLlama-34b-Instruct \
#     --tasks ${task} --batch_size 1 --no_cache  \
# >>CodeLlama-34b-Instruct-skip-4-4-${task}.txt 2>&1 &


task=hellaswag
export ENDPOINT=http://127.0.0.1:8080/generate && \
python -u main.py \
    --model tgi \
    --model_args pretrained=/dev/shm/data/CodeLlama-34b-Instruct \
    --tasks ${task} --batch_size 1 --no_cache --limit 100 \
>>CodeLlama-34b-Instruct-FT1K-async-4-4-${task}.txt 2>&1 &

wait
