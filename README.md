# ac-competition-history

Crawler should contain 2 parts:
* Crawl history of the active users
* Update data after each contest

## How to setup

### .env
Rename `.env.example` to `.env` then the github token to it.

```
GITHUB_TOKEN=github_pat_...
ATCODER_USER_NAME=...
ATCODER_PASSWORD=...
DEBUG=0 or 1 # if DEBUG = 1, the data generated by this program will be not pushed to github
```

### Get initial data
> Run one time

```shell
# Start from page 1, get data of algo contests
python once.py --type algo
# Specify start_page to get data
python once.py --type heuristic --start_page 3
```

### Run to update data
> Run for long period

```shell
python main.py
```

### Reference
https://data.ac-predictor.com/aperfs/arc178.json

### TODO
* Get the competition history of users 1 hour before the contest starts (generating during contests is slow)
* Repo https://github.com/conlacda/ac-perf-data sẽ dùng để chạy, đơn giản là copy code từ đây sang rồi ignore hết mọi thứ đi, thư mục đó sẽ dùng để lưu trữ dữ liệu.
* Chờ rasberry pi về rồi thử chạy lâu dài xem kết quả có đúng ko - cứ so sánh với tool kia là xong
* Viết thêm giao diện cho phần virtual standing + heuristic (phần algo cả trước và sau contest đều xong rồi)
* Need to check: _kasugano_urara - người này có phần performance hiển thị và performance lấy từ json ko giống nhau??
* Hiện tại phần code ở đây đang dùng InnerPerformance - lưu trong data/ và tính toán dựa trên innerperformance rồi update lại vào đây. Nhưng thực tế Performance cũng cần để tính ra rating -> cần thay đổi dữ liệu bên trong data/. Thay vì mỗi người là 1 mảng [InnerPerf, InnerPerf] thì giờ sẽ là 
```js
{
    "InnerPerformance": ["100", "3000", ..], // dùng để tính aperf -> perfArr
    "Performance": ["100", "2400", ..] // dùng để tính rating của từng người cal_from_perf_arr([])
}
```