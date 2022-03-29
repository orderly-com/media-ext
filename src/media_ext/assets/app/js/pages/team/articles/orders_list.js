$(function() {

    moment.locale("zh_tw");

    var csrfmiddlewaretoken = $('input[name="csrfmiddlewaretoken"]').val()
    ,   $content = $("#content")
    ,   date_start = $content.attr("data-date_start")
    ,   date_end = $content.attr("data-date_end")
    ,   hashes = window.location.href.slice(window.location.href.indexOf("?") + 1).split("&")
    ,   search_keys = ""
    ;

    // choice
    $(".styled").uniform({
        radioClass: "choice"
    });


    // assign search_keys in querystring to search_keys field
    for(var i = 0; i < hashes.length; i++){
        hash = hashes[i].split("=");
        if (hash[0] == "search_keys"){
            search_keys = decodeURIComponent(hash[1])
            $("#serach-key").val(search_keys);
        }
    }

    $(".daterange-ranges").daterangepicker(
        {
            startDate: date_start,
            endDate: date_end,
            ranges: {
                "今天": [moment(), moment()],
                "昨天": [moment().subtract(1, "days"), moment().subtract(1, "days")],
                "近 7 天": [moment().subtract(6, "days"), moment()],
                "近 28 天": [moment().subtract(27, "days"), moment()],
                "近半年": [moment().subtract(179, "days"), moment()],
                "近一年": [moment().subtract(11, "month").startOf("month"), moment().endOf("month")],
                "不拘": [moment("1970-01-01"), moment()],
            },
            alwaysShowCalendars:true,
            opens: "left",
            applyButtonClasses: "btn-small btn-yellow",
            cancelButtonClasses: "btn-small btn-gray",
            locale: { cancelLabel: "取消", applyLabel: "確認","customRangeLabel": "區間選擇",}
        },
        function(start, end) {

            $(".daterange-ranges span").html(start.format("YYYY-MM-DD") + " &nbsp; - &nbsp; " + end.format("YYYY-MM-DD"));

            date_start = start.format("YYYY-MM-DD")
            date_end = end.format("YYYY-MM-DD")

            $("#btn-search").click()

        }
    );

    $(".daterange-ranges span").html(date_start + " &nbsp; - &nbsp; " + date_end);

    function dateFromNow(date_text) {

        var input_date = moment(date_text);
        var dateEnd = moment(date_end)
        var duration = moment.duration(dateEnd.diff(input_date))
        var year = duration.get("years");
        var month = duration.get("months");
        var day = duration.get("days");
        if (month > 0 ||year > 0) {
            var return_text = year + " 年 " + month + " 個月"
        } else {
            var return_text = day + " 天"
        }
        return return_text
    }

    function calculateDateGap() {
        var dates = ["#article-detail #article-date #article-data",
        ]
        dates.forEach(function (element) {
            var date_text = $(element).text()
            var result = dateFromNow(date_text)
            $(element).text(result)
        }
        )
    };

    calculateDateGap();

    $("#serach-key").keyup(function(event) {
        if (event.keyCode === 13) {
            $("#btn-search").click();
        }
    });

    $(".btn-search")
    .click(function(e){

        var search_keys = $("#serach-key").val(),
            enabled_status_list = $.map($('input[name="status"]:checked'), function(c){return c.value; }),
            enabled_source_list = $.map($('input[name="source"]:checked'), function(c){return c.value; }),
            article_type = $('input[name="article-type"]:checked').val();

        search_keys = encodeURIComponent(search_keys);

        StartLoadingBlock(".block-when-runnning");

        params = {
            "date_start":date_start,
            "date_end":date_end,
            "article_type":article_type,
            "search_keys":search_keys,
            "enabled_status_list":enabled_status_list,
            "enabled_source_list":enabled_source_list,
        }

        var recursiveEncoded = $.param(params);

        window.location = "/team/articles/?"+recursiveEncoded

    })


    $(".list_operation")
    .click(function(e){

        var $this = $(this)
        ,   action = $this.attr("data-action")
        ,   target = $this.attr("data-target")
        ;

        if (action == "select_all"){
            $("input[name='"+ target +"']").prop("checked", true);
            $.uniform.update("input[name='"+ target +"']");
        }
        else if (action == "cancle_all"){
            $("input[name='"+ target +"']").prop("checked", false);
            $.uniform.update("input[name='"+ target +"']");
        }
        else{
            ;
        }

        e.preventDefault();

    })

});
