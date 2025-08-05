$(document).ready(function () {
    $.ajax({
        url: "/history/all",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({}), // 若有登录凭证需带上 credentials
        success: function (response) {
            const tableData = response.data.map(row => {
                const psgLink = row.psg
                    ? `<a href="/report/${row.uid}" class="badge bg-success text-decoration-none">已生成</a>`
                    : `<a href="/report/${row.uid}" class="badge bg-secondary text-decoration-none">未生成</a>`;

                const cdgLink = row.cdg
                    ? `<a href="/note/${row.uid}" class="badge bg-success text-decoration-none">已生成</a>`
                    : `<a href="/note/${row.uid}" class="badge bg-secondary text-decoration-none">未生成</a>`;

                const actionBtns = `
                <button class="btn btn-danger btn-sm delete-btn" data-uid="${row.uid}">删除</button>
                <a href="/admin/detail/${row.uid}" target="_blank" class="btn btn-default btn-sm">细节</a>`;

                return [
                    row.uid,
                    psgLink,
                    cdgLink,
                    row.time,
                    actionBtns,
                ];
            });

            const table = $('#historyTable').DataTable({
                data: tableData,
                columns: [
                    {title: "UID"},
                    {title: "患者报告"},
                    {title: "病历记录"},
                    {title: "创建时间"},
                    {title: "操作"}
                ],
                pageLength: 10,
                language: {
                    url: "https://cdn.datatables.net/plug-ins/1.13.6/i18n/zh.json"
                }
            });

            // 绑定删除按钮事件
            $('#historyTable tbody').on('click', '.delete-btn', function () {
                const uid = $(this).data('uid');
                const row = $(this).closest('tr');

                if (confirm(`确认删除 UID: ${uid} 吗？`)) {
                    fetch(`/admin/${uid}`, {
                        method: "DELETE",
                        credentials: "include"
                    })
                        .then(async (res) => {
                            const result = await res.json();
                            if (res.ok && result.status === "success") {
                                alert(result.message || "删除成功");
                                $('#historyTable').DataTable().row(row).remove().draw();
                            } else {
                                alert(result.message || "删除失败");
                            }
                        })
                        .catch(() => {
                            alert("请求出错，请稍后重试");
                        });
                }
            });

        },
        error: function () {
            alert("加载数据失败！");
        }
    });
});